from typing import List
from flask import render_template, redirect, request, url_for, flash
from flask_login import current_user, login_required
from app.main import bp
from app.models import User, Experiment, Action
from app.experiment.forms import RunExperimentForm
from app.experiment.routes import runExperiment
from Helper import Config

config = Config()
branding = config.Branding

@bp.route('/', methods=['GET', 'POST'])
@bp.route('/index/reload', methods=['GET', 'POST'])  # TODO: Use URL params or other solution
@bp.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    notices: List[str] = config.Notices
    actions: List[Action] = User.query.get(current_user.id).Actions
    experiments: List[Experiment] = current_user.Experiments
    formRun = RunExperimentForm()
    if formRun.validate_on_submit():
        success = runExperiment()
        return redirect(f"{request.host_url}index/reload") if success else redirect(request.url)

    return render_template('index.html', formRun=formRun, experiments=experiments, notices=notices,
                           platformName=branding.Platform, header=branding.Header, favicon=branding.FavIcon,
                           actions=actions, ewEnabled=Config().EastWest.Enabled)


@bp.route('/info', methods=['GET', 'POST'])
def info():
    if request.method == 'POST':
        new_html = request.form.get('content')
        with open(branding.DescriptionPage, 'w', encoding='utf8') as page:
            page.write(new_html)
        flash("Content saved successfully.")
        return redirect(url_for('main.info'))

    with open(branding.DescriptionPage, 'r', encoding='utf8') as page:
        html = page.read()

    return render_template('info.html', title="Testbed Info", favicon=branding.FavIcon,
                           platformName=branding.Platform, header=branding.Header, html=html,
                           ewEnabled=Config().EastWest.Enabled)
