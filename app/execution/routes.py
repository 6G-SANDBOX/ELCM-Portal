from flask import render_template, flash, redirect, url_for
from flask_login import current_user, login_required
from typing import Dict
from app import db
from app.execution import bp
from app.models import Experiment, Execution
from Helper import Config, LogInfo, Log
from REST import ElcmApi, AnalyticsApi

config = Config()
branding = config.Branding

@bp.route('/<int:executionId>', methods=['GET'])
@login_required
def execution(executionId: int):
    def _responseToLogList(response):
        return [LogInfo(response["PreRun"]), LogInfo(response["Executor"]), LogInfo(response["PostRun"])]

    execution: Execution = Execution.query.get(executionId)
    if execution is None:
        Log.I(f'Execution not found')
        flash(f'Execution not found', 'error')
        return redirect(url_for('main.index'))

    else:
        experiment: Experiment = Experiment.query.get(execution.experiment_id)
        if experiment.user_id is current_user.id:
            try:
                # Get Execution logs information
                localResponse: Dict = ElcmApi().GetLogs(executionId)
                Log.D(f'Access execution logs response {localResponse}')
                status = localResponse["Status"]
                if status == 'Success':
                    localLogs = _responseToLogList(localResponse)
                    remoteLogs = None
                    analyticsUrl = \
                        AnalyticsApi().GetUrl(executionId, current_user) if config.Analytics.Enabled else None

                    if experiment.remoteDescriptor is not None:
                        success = False
                        peerId = ElcmApi().GetPeerId(executionId)
                        if peerId is not None:
                            remote = config.EastWest.RemoteApi(experiment.remotePlatform)
                            if remote is not None:
                                try:
                                    remoteResponse = remote.GetExecutionLogs(peerId)
                                    if remoteResponse['Status'] == 'Success':
                                        remoteLogs = _responseToLogList(remoteResponse)
                                        success = True
                                except Exception: pass
                        if not success:
                            flash('Could not retrieve remote execution logs', 'warning')

                    return render_template('execution/execution.html', title=f'Execution {execution.id}',
                                           platformName=branding.Platform, header=branding.Header, favicon=branding.FavIcon,
                                           execution=execution, localLogs=localLogs, remoteLogs=remoteLogs,
                                           experiment=experiment, grafanaUrl=config.GrafanaUrl,
                                           executionId=getLastExecution() + 1,
                                           dispatcherUrl=config.ELCM.Url, analyticsUrl=analyticsUrl,
                                           ewEnabled=config.EastWest.Enabled)
                else:
                    if status == 'Not Found':
                        message = "Execution not found"
                    else:
                        message = f"Could not connect with log repository: {status}"
                    Log.I(message)
                    flash(message, 'error')
                    return redirect(url_for('experiment.experiment', experimentId=experiment.id))

            except Exception as e:
                Log.E(f'Error accessing execution{execution.experiment_id}: {e}')
                flash(f'Exception while trying to connect with dispatcher: {e}', 'error')
                return redirect(url_for('experiment.experiment', experimentId=experiment.id))
        else:
            Log.I(f'Forbidden - User {current_user.name} don\'t have permission to access execution{executionId}')
            flash(f'Forbidden - You don\'t have permission to access this execution', 'error')
            return redirect(url_for('main.index'))


def getLastExecution() -> int:
    return db.session.query(Execution).order_by(Execution.id.desc()).first().id

@bp.route('/<int:executionId>/cancel', methods=['GET'])
@login_required
def cancel_execution(executionId: int):
    try:
        execution: Execution = Execution.query.get(executionId)
        if not execution:
            Log.W(f'Execution {executionId} not found.')
            flash(f'Execution {executionId} not found.', 'warning')
            return redirect(url_for('execution.execution', executionId=executionId))

        Log.D(f'Attempting to cancel execution {executionId}, current status: {execution.status}')

        if execution.status == 'Finished':
            Log.W(f'Execution {executionId} is already finished, cannot cancel.')
            flash(f'Cannot cancel execution {executionId} because it is already finished.', 'warning')
            return redirect(url_for('execution.execution', executionId=executionId))

        response = ElcmApi().CancelExecution(executionId)
        if response.get("success"):
            Log.I(f'Execution {executionId} cancelled successfully.')
            flash(f'Execution {executionId} cancelled successfully', 'success')
        else:
            error_message = response.get("message", "No message provided")
            Log.E(f'Failed to cancel execution {executionId}, {error_message}.')
            flash(f'Failed to cancel execution {executionId}: {error_message}', 'error')
    except Exception as e:
        Log.E(f'Unexpected error while cancelling execution {executionId}: {e}')
        flash(f'Unexpected error cancelling execution: {e}', 'error')

    return redirect(url_for('execution.execution', executionId=executionId))

@bp.route('/<int:executionId>/testcases', methods=['GET'])
@login_required
def execution_test_cases(executionId: int):
    execution: Execution = Execution.query.get(executionId)
    if not execution:
        flash("Execution not found", "error")
        return redirect(url_for('main.index'))

    experiment: Experiment = Experiment.query.get(execution.experiment_id)
    if experiment.user_id != current_user.id:
        flash("Unauthorized access", "danger")
        return redirect(url_for('main.index'))

    try:
        elcm = ElcmApi()
        response = elcm.GetExecutionInfo(executionId)
        testcases = response.get("TestCases", {})
        ues = response.get("UEs", {})
    except Exception as e:
        flash(f"Error fetching execution test cases: {e}", "error")
        testcases = {}
        ues = {}

    return render_template(
        'execution/test_cases.html',
        execution=execution,
        testcases=testcases,
        ues=ues,
        platformName=branding.Platform,
        header=branding.Header,
        favicon=branding.FavIcon
    )
