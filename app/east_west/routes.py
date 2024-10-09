from app.east_west import bp
from flask import jsonify
from Helper import Facility
from REST import ElcmApi


@bp.route('/testcases', methods=['GET'])
def testcases():
    return jsonify({'TestCases': Facility.DistributedTestCases()})


@bp.route('/ues', methods=['GET'])
def ues():
    return jsonify({'UEs': Facility.UEs()})


@bp.route('/scenarios', methods=['GET'])
def scenarios():
    return jsonify({'Scenarios': Facility.Scenarios()})


@bp.route('/networkServices', methods=['GET'])
def networkServices():
    return jsonify({
        'NetworkServices': []  # TODO: Cleanup
    })


@bp.route('/executionLogs/<executionId>', methods=['GET'])
def executionLogs(executionId: int):
    return ElcmApi().GetLogs(executionId)
