import os

from flask import Flask

from . import auth, finances, params, system


def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(SECRET_KEY="dev")

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile("config.py", silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # ensure the instance folder exists
    if not os.path.exists(app.instance_path):
        os.makedirs(app.instance_path)

    app.register_blueprint(auth.bp)
    app.register_blueprint(finances.bp)
    app.register_blueprint(system.bp)
    app.register_blueprint(params.bp)
    app.add_url_rule("/", endpoint="index")

    return app
