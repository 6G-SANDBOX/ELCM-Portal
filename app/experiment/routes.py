from datetime import datetime, timezone
from typing import Dict, List, Tuple, Set
from flask import render_template, flash, redirect, url_for, request, jsonify, abort, Response
from flask.json import loads as jsonParse
from flask_login import current_user, login_required
from REST import ElcmApi, AnalyticsApi
from app import db
from app.experiment import bp
from app.models import Experiment, Execution, Action
from app.experiment.forms import ExperimentForm, RunExperimentForm, DistributedStep1Form, DistributedStep2Form
from app.execution.routes import getLastExecution
from Helper import Config, Log, Facility
from datetime import datetime, timedelta
import io, yaml
from werkzeug.datastructures import FileStorage


config = Config()
branding = config.Branding

@bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    Facility.Reload()
    experimentTypes = ['Standard', 'Custom', 'MONROE']
    scenarios = Facility.Scenarios()
    scenarios = ['None'] if len(scenarios) == 0 else scenarios

    form = ExperimentForm()
    if form.validate_on_submit():
        experimentName = request.form.get('name')
        experimentType = request.form.get('type')
        exclusive = (len(request.form.getlist('exclusive')) != 0)

        testCases = request.form.getlist(f'{experimentType}_testCases')
        ues_selected = request.form.getlist(f'{experimentType}_ues')
        scenario = request.form.get('scenarioCheckboxedList')
        scenario = None if scenario == 'None' else scenario

        parameters = {}
        if experimentType == "Custom":
            for key, value in request.form.items():
                key = str(key)
                if key.endswith('_ParameterTextField') and len(value) != 0:
                    parameters[key.replace('_ParameterTextField', '')] = value
        elif experimentType == "MONROE":
            rawParams = request.form.get('monroeParameters')
            if rawParams is not None:
                rawParams = '{}' if len(rawParams) == 0 else rawParams  # Minimal valid JSON
                try:
                    parameters = jsonParse(rawParams)
                except Exception as e:
                    flash(f'Exception while parsing Parameters: {e}', 'error')
                    return redirect(url_for("experiment.create"))

        automated = (len(request.form.getlist('automate')) != 0) if experimentType == "Custom" else True
        possibleTimes = {'Standard': None,
                         'Custom': None if automated else int(request.form.get('reservationCustom')),
                         'MONROE': int(request.form.get('reservationMonroe'))}
        reservationTime = possibleTimes[experimentType]

        application = request.form.get('application') if experimentType == "MONROE" else None

        experiment = Experiment(
            name=experimentName, author=current_user,
            type=experimentType, exclusive=exclusive,
            test_cases=testCases, ues=ues_selected, scenario=scenario,
            automated=automated, reservation_time=reservationTime,
            parameters=parameters, application=application,
        )

        db.session.add(experiment)
        db.session.commit()

        Log.I(f'Added experiment {experiment.id}')

        action: Action = Action(timestamp=datetime.now(timezone.utc), author=current_user,
                                message=f'<a href="/experiment/{experiment.id}">Created experiment: {experimentName}</a>')
        db.session.add(action)
        db.session.commit()
        Log.I(f'Added action - Created experiment')
        flash('Your experiment has been successfully created', 'info')
        return redirect(url_for('main.index'))

    customTestCases = Facility.AvailableCustomTestCases(current_user.email)
    parametersPerTestCase = Facility.TestCaseParameters()
    parameterNamesPerTestCase: Dict[str, Set[str]] = {}
    testCaseNamesPerParameter: Dict[str, Set[str]] = {}
    parameterInfo: Dict[str, Dict[str, str]] = {}
    for testCase in customTestCases:
        parameters = parametersPerTestCase[testCase]
        for parameter in parameters:
            name = parameter['Name']
            parameterInfo[name] = parameter

            if testCase not in parameterNamesPerTestCase.keys():
                parameterNamesPerTestCase[testCase] = set()
            parameterNamesPerTestCase[testCase].add(name)

            if name not in testCaseNamesPerParameter.keys():
                testCaseNamesPerParameter[name] = set()
            testCaseNamesPerParameter[name].add(testCase)

    return render_template('experiment/create.html', title='New Experiment',
                           platformName=branding.Platform, header=branding.Header, favicon=branding.FavIcon,
                           form=form, standardTestCases=Facility.StandardTestCases(), ues=Facility.UEs(),
                           customTestCases=customTestCases, parameterInfo=parameterInfo, scenarios=scenarios,
                           parameterNamesPerTestCase=parameterNamesPerTestCase,
                           testCaseNamesPerParameter=testCaseNamesPerParameter,
                           experimentTypes=experimentTypes, ewEnabled=config.EastWest.Enabled)


@bp.route('/create_dist', methods=['GET', 'POST'])
@login_required
def createDist():
    Facility.Reload()
    eastWest = config.EastWest
    if not eastWest.Enabled:
        return abort(404)

    form = DistributedStep1Form()
    if form.validate_on_submit():
        try:
            experimentName = request.form.get('name')
            exclusive = (len(request.form.getlist('exclusive')) != 0)
            testCases = request.form.getlist('Distributed_testCases')
            ues_selected = request.form.getlist('Distributed_ues')
            remotePlatform = request.form.get('remoteSelectorCheckboxedList')

            experiment = Experiment(
                name=experimentName, author=current_user,
                type="Distributed", exclusive=exclusive,
                test_cases=testCases, ues=ues_selected,
                automated=True, reservation_time=None,
                parameters={}, application=None,
                remotePlatform=remotePlatform, remoteDescriptor=None
            )

            db.session.add(experiment)
            db.session.commit()

            Log.I(f'Added experiment {experiment.id}')
            return redirect(url_for('experiment.configureRemote', experimentId=experiment.id))
        except Exception as e:
            flash(f'Exception creating distributed experiment (local): {e}', 'error')

    remotes = eastWest.RemoteNames
    nss: List[Tuple[str, int]] = []  # TODO: Cleanup

    return render_template('experiment/create_dist.html', title='New Distributed Experiment',
                           platformName=branding.Platform, header=branding.Header, favicon=branding.FavIcon, form=form,
                           nss=nss, sliceList=Facility.BaseSlices(), scenarioList=["[None]", *Facility.Scenarios()],
                           ues=Facility.UEs(), ewEnabled=eastWest.Enabled, remotes=remotes,
                           distributedTestCases=Facility.DistributedTestCases())


@bp.route('/configure_remote/<experimentId>', methods=['GET', 'POST'])
@login_required
def configureRemote(experimentId: int):
    eastWest = config.EastWest
    if not eastWest.Enabled:
        return abort(404)

    localExperiment: Experiment = Experiment.query.get(experimentId)
    if localExperiment is None:
        flash(f'Experiment not found', 'error')
        return redirect(url_for('main.index'))

    if localExperiment.user_id is None or localExperiment.user_id is not current_user.id:
        flash(f'Forbidden - You don\'t have permission to access this experiment', 'error')
        return redirect(url_for('main.index'))

    remoteApi = eastWest.RemoteApi(localExperiment.remotePlatform)
    if remoteApi is None:
        flash(f"Unknown remote platform '{localExperiment.remotePlatform}'", 'error')
        return redirect(url_for('main.index'))

    testCases = remoteApi.GetTestCases()
    ues = remoteApi.GetUEs()

    form = DistributedStep2Form()
    if form.validate_on_submit():
        try:
            experimentName = f'{localExperiment.name}__remote'
            exclusive = localExperiment.exclusive
            testCases = request.form.getlist('RemoteSide_testCases')
            ues_selected = request.form.getlist('RemoteSide_ues')

            experiment = Experiment(
                name=experimentName, author=None,
                type="RemoteSide", exclusive=exclusive,
                test_cases=testCases, ues=ues_selected,
                automated=True, reservation_time=None,
                parameters={}, application=None,
                remotePlatform=None, remoteDescriptor=None,
                parentDescriptor=[localExperiment],
                remoteNetworkServices=None
            )

            db.session.add(experiment)
            db.session.commit()

            localExperiment.remoteDescriptor = experiment
            db.session.add(localExperiment)
            db.session.commit()

            Log.I(f'Added experiment {experiment.id}')
            flash('Your experiment has been successfully created', 'info')
            return redirect(url_for('main.index'))
        except Exception as e:
            flash(f'Exception creating distributed experiment (local): {e}', 'error')

    return render_template('experiment/configure_dist.html', title='New Distributed Experiment',
                           platformName=branding.Platform, header=branding.Header, favicon=branding.FavIcon,
                           form=form, localExperiment=localExperiment,
                           testCases=testCases, ues=ues)


@bp.route('/<experimentId>/reload', methods=['GET', 'POST'])
@bp.route('/<experimentId>', methods=['GET', 'POST'])
@login_required
def experiment(experimentId: int):
    exp: Experiment = Experiment.query.get(experimentId)
    formRun = RunExperimentForm()
    if formRun.validate_on_submit():
        success = runExperiment()
        return redirect(f"{request.url}/reload") if success else redirect(request.url)

    if exp is None:
        Log.I(f'Experiment not found')
        flash(f'Experiment not found', 'error')
        return redirect(url_for('main.index'))
    else:
        if exp.user_id is not None and exp.user_id is current_user.id:

            # Get Experiment's executions
            executions: List[Experiment] = exp.experimentExecutions()
            if len(executions) == 0:
                flash(f"The experiment '{exp.name}' doesn't have any executions yet", 'info')
                return redirect(url_for('main.index'))
            else:
                analyticsApi = AnalyticsApi()
                analyticsUrls = {}
                analyticsEnabled = config.Analytics.Enabled
                for execution in executions:
                    analyticsUrls[execution.id] = \
                        analyticsApi.GetUrl(execution.id, current_user) if analyticsEnabled else None

                return render_template('experiment/experiment.html', title=f'Experiment: {exp.name}',
                                       experiment=exp, platformName=branding.Platform, favicon=branding.FavIcon,
                                       header=branding.Header, executions=executions, formRun=formRun,
                                       grafanaUrl=config.GrafanaUrl, executionId=getLastExecution() + 1,
                                       dispatcherUrl=config.ELCM.Url, analyticsUrls=analyticsUrls,
                                       ewEnabled=config.EastWest.Enabled)
        else:
            Log.I(f'Forbidden - User {current_user.username} don\'t have permission to access experiment {experimentId}')
            flash(f'Forbidden - You don\'t have permission to access this experiment', 'error')
            return redirect(url_for('main.index'))


def runExperiment() -> bool:
    """Returns true if no issue has been detected"""
    try:
        jsonResponse: Dict = ElcmApi().Run(int(request.form['id']))

        if jsonResponse.get("success") is False or "ExecutionId" not in jsonResponse:
            
            Log.E(f"Failed to start experiment: {jsonResponse}")
            flash(f"{jsonResponse.get('message', 'Unknown error')}", 'error')
            return False

        executionId = jsonResponse["ExecutionId"]

        Log.I(f'Ran experiment {request.form["id"]}')
        Log.D(f'Ran experiment response {jsonResponse}')
        flash(f'Experiment started with Execution Id: {executionId}', 'info')
        execution: Execution = Execution(id=executionId, experiment_id=request.form['id'], status='Init')
        db.session.add(execution)
        db.session.commit()

        Log.I(f'Added execution {jsonResponse["ExecutionId"]}')
        exp: Experiment = Experiment.query.get(execution.experiment_id)
        action = Action(timestamp=datetime.now(timezone.utc), author=current_user,
                        message=f'<a href="/execution/{execution.id}">Ran experiment: {exp.name}</a>')
        db.session.add(action)
        db.session.commit()
        Log.I(f'Added action - Ran experiment')
        return True

    except Exception as e:
        Log.E(f'Error running experiment: {e}')
        flash(f'Exception while trying to connect with dispatcher: {e}', 'error')
        return False


@bp.route('/<experimentId>/descriptor', methods=["GET"])
@login_required
def descriptor(experimentId: int):
    experiment = Experiment.query.get(experimentId)
    if experiment is None:
        flash('Experiment not found', 'error')
        return redirect(url_for('main.index'))
    elif experiment.user_id is None or experiment.user_id != current_user.id:
        flash("Forbidden - You don't have permission to access this experiment", 'error')
        return redirect(url_for('main.index'))
    else:
        return jsonify(experiment.serialization())


@bp.route('/kickstart/<experimentId>', methods=["GET"])
def kickstart(experimentId: int):
    try:
        Log.I(f"KS: Kickstarting experiment {experimentId}")
        jsonResponse: Dict = ElcmApi().Run(experimentId)
        execution: Execution = Execution(id=jsonResponse["ExecutionId"], experiment_id=experimentId, status='Init')
        db.session.add(execution)
        db.session.commit()
        Log.I(f'KS: Added execution {jsonResponse["ExecutionId"]}')

        return f'Hush now! Exp {experimentId} - Exec {jsonResponse["ExecutionId"]}'
    except Exception as e:
        return str(e)
        
@bp.route('/delete/<int:experiment_id>', methods=['POST'])
@login_required
def delete_experiment(experiment_id):
    
    experiment = Experiment.query.get_or_404(experiment_id)

    # Check if the current user has permission to delete the experiment
    if experiment.user_id != current_user.id:
        flash("You do not have permission to delete this experiment.", "danger")
        return redirect(url_for('main.index'))

    # Retrieve all executions related to the experiment
    executions = experiment.experimentExecutions() or []
    
    # Instantiate the API client
    api = ElcmApi()
    
    # Cancel each execution using the cancel endpoint
    for exe in executions:
        try:
            response=ElcmApi().CancelExecution(exe.id)
            
            if not response.get("success"):
                error_message = response.get("message", "No message provided")
                Log.W(f"Cancellation for execution {exe.id} did not return status 200 (got {error_message}).")
                flash(f"Error canceling execution {exe.id}. Please try again.", "warning")
                return redirect(url_for('main.index'))
        except Exception as e:
            Log.E(f"Error canceling execution {exe.id}: {e}")
            flash(f"Error canceling execution {exe.id}: {e}", "error")
            return redirect(url_for('main.index'))

    Execution.query.filter_by(experiment_id=experiment_id).delete()

    db.session.delete(experiment)
    db.session.commit()
    flash("Experiment and its executions have been cancelled and deleted.", "success")
    return redirect(url_for('main.index'))

@bp.route('/delete_test_case', methods=['POST'])
@login_required
def delete_test_case():
    test_case_name = request.json.get('test_case_name')
    file_type = request.json.get('file_type', 'testcase')

    if not test_case_name:
        return jsonify({"success": False, "message": "No test case name provided"}), 400

    try:
        response = ElcmApi().delete_test_case(test_case_name, file_type)
        Facility.Reload()
        if "error" in response:
            return jsonify({"success": False, "message": response["error"]}), 500

        if response.get("success", False):
            return jsonify({
                "success": True,
                "message": f"{file_type} {test_case_name} deleted via ELCM API"
            })
        else:
            return jsonify({"success": False, "message": f"Failed to delete {file_type}: {response}"}), 400

    except Exception as e:
        return jsonify({"success": False, "message": f"Exception: {str(e)}"}), 500


@bp.route('/upload_test_case', methods=['POST'])
@login_required
def upload_test_case():
    file = request.files.get('test_case')
    file_type = request.form.get('file_type', 'testcase')

    if not file:
        return jsonify({"success": False, "message": "No file received"}), 400

    if not file.filename.lower().endswith('.yml'):
        return jsonify({"success": False, "message": "Invalid file extension. Only .yml allowed."}), 400

    try:
        response = ElcmApi().upload_test_case(file,file_type)
        Facility.Reload()
        if response.get("success", False):
            return jsonify({"success": True, "message": f"Test case {file.filename} uploaded via ELCM API. Type: {file_type}"})
        else:
            return jsonify({"success": False, "message": f"Failed to upload test case: {response}"}), 400

    except Exception as e:
        return jsonify({"success": False, "message": f"Exception: {str(e)}"}), 500

@bp.route('/<experimentId>/test_cases', methods=['GET'])
@login_required
def test_cases(experimentId: int):
    experiment = Experiment.query.get(experimentId)
    if experiment is None:
        flash('Experiment not found', 'error')
        return redirect(url_for('main.index'))
    
    if experiment.user_id != current_user.id:
        flash("Unauthorized access", "danger")
        return redirect(url_for('main.index'))

    test_case_names = experiment.test_cases or []
    ue_names = experiment.ues or []
    scenario_names = [experiment.scenario] if experiment.scenario else []

    api = ElcmApi()
    facility_data = api.GetTestCasesInfo(
        test_cases=test_case_names,
        ues=ue_names,
        scenarios=scenario_names
    ) or {}

    return render_template(
        'experiment/test_cases.html',
        experiment=experiment,
        filtered_test_cases=facility_data.get("TestCases", {}),
        filtered_ues=facility_data.get("UEs", {}),
        filtered_scenarios=facility_data.get("Scenarios", {}),
        platformName=branding.Platform,
        header=branding.Header,
        favicon=branding.FavIcon
    )

@bp.route('/edit_test_case', methods=['GET', 'POST'])
@login_required
def edit_test_case():
    name = request.form.get('test_case_name') or request.args.get('test_case_name')
    file_type = request.args.get('file_type', 'testcase')
    
    if file_type not in ('testcase', 'ues', 'scenarios'):
        flash("Invalid file type.", 'danger')
        return redirect(url_for('experiment.create'))

    elcm = ElcmApi()

    if request.method == 'GET':
        # Fetch raw YAML entries from ELCM using unified method
        info = elcm.GetTestCasesInfo(
            test_cases=[name] if file_type == 'testcase' else [],
            ues=[name] if file_type == 'ues' else [],
            scenarios=[name] if file_type == 'scenarios' else []
        )

        bucket_key = {
            'testcase': 'TestCases',
            'ues': 'UEs',
            'scenarios': 'Scenarios'
        }[file_type]

        entries = info.get(bucket_key, {}).get(name, []) if info else []

        if not entries:
            flash(f"{file_type} '{name}' does not exist in ELCM.", 'warning')
            return redirect(url_for('experiment.create'))

        # Join multiple YAML documents if needed
        content = "\n---\n".join(entries)
        return render_template(
            'experiment/edit_test_case.html',
            test_case_name=name,
            file_type=file_type,
            content=content,
            platformName=branding.Platform,
            header=branding.Header,
            favicon=branding.FavIcon
        )

    # POST: validate YAML and upload back to ELCM
    new_yaml = request.form.get('yaml_content', '')
    if not new_yaml.strip():
        flash("YAML content cannot be empty.", 'danger')
        return render_template(
            'experiment/edit_test_case.html',
            test_case_name=name,
            file_type=file_type,
            content=new_yaml,
            platformName=branding.Platform,
            header=branding.Header,
            favicon=branding.FavIcon
        )
    
    try:
        yaml.safe_load(new_yaml)
    except yaml.YAMLError as e:
        flash(f"Invalid YAML: {e}", 'danger')
        return render_template(
            'experiment/edit_test_case.html',
            test_case_name=name,
            file_type=file_type,
            content=new_yaml,
            platformName=branding.Platform,
            header=branding.Header,
            favicon=branding.FavIcon
        )

    # Wrap the edited YAML in a FileStorage so the ELCM client can process it
    bytes_io = io.BytesIO(new_yaml.encode('utf-8'))
    file_storage = FileStorage(
        stream=bytes_io,
        filename=f"{name}.yml",
        content_type="application/x-yaml"
    )

    resp = elcm.edit_test_case(file_storage, file_type)
    if resp.get('success'):
        flash(resp.get('message'), 'success')
    else:
        flash(resp.get('message'), 'danger')

    return redirect(url_for('experiment.create'))

@bp.route('/download_test_case', methods=['GET'])
@login_required
def download_test_case():
    test_case_name = request.args.get('test_case_name')
    file_type      = request.args.get('file_type', 'testcase')

    info = ElcmApi().GetTestCasesInfo(
        test_cases=[test_case_name] if file_type == 'testcase' else [],
        ues       =[test_case_name] if file_type == 'ues'      else [],
        scenarios =[test_case_name] if file_type == 'scenarios' else []
    ) or {}

    bucket_key = {
        'testcase':  'TestCases',
        'ues':       'UEs',
        'scenarios': 'Scenarios'
    }.get(file_type)

    entries = info.get(bucket_key, {}).get(test_case_name, [])
    if not entries:
        abort(404, description=f"{file_type} '{test_case_name}' not found")

    content = "\n---\n".join(entries)
    return Response(
        content,
        mimetype='application/x-yaml',
        headers={'Content-Disposition': f'attachment; filename="{test_case_name}.yml"'}
    )

@bp.route('/create_test_case', methods=['GET', 'POST'])
@login_required
def create_test_case():
    if request.method == 'POST':
        content = request.form.get('yaml_content')
        file_type = request.form.get('file_type', 'testcase')

        if not content:
            flash("YAML content is required.", "warning")
            return redirect(url_for('experiment.create_test_case'))

        try:
            data = yaml.safe_load(content)
        except yaml.YAMLError as e:
            flash(f"Invalid YAML: {e}", "danger")
            return redirect(url_for('experiment.create_test_case'))

        if isinstance(data, dict) and "Name" in data:
            internal_name = data["Name"]
        elif isinstance(data, dict):
            internal_name = next(iter(data.keys()))
        else:
            flash("YAML must be a mapping with a 'Name' field or a single root key.", "danger")
            return redirect(url_for('experiment.create_test_case'))

        file_stream = io.BytesIO(content.encode('utf-8'))
        filename = f"{internal_name}.yml"
        file_storage = FileStorage(
            stream=file_stream,
            filename=filename,
            content_type='application/x-yaml'
        )

        elcm = ElcmApi()
        response = elcm.upload_test_case(file_storage, file_type)

        if response.get("success"):
            flash(f"{response.get('message')}", "success")
            return redirect(url_for('experiment.create'))
        else:
            flash(f"Error creating {file_type.capitalize()}: {response.get('message')}", "danger")
            return redirect(url_for('experiment.create_test_case'))

    return render_template(
        'experiment/create_test_case.html',
        platformName=branding.Platform,
        header=branding.Header,
        favicon=branding.FavIcon
    )
