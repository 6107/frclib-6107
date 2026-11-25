# ------------------------------------------------------------------------ #
#      o-o      o                o                                         #
#     /         |                |                                         #
#    O     o  o O-o  o-o o-o     |  oo o--o o-o o-o                        #
#     \    |  | |  | |-' |   \   o | | |  |  /   /                         #
#      o-o o--O o-o  o-o o    o-o  o-o-o--O o-o o-o                        #
#             |                           |                                #
#          o--o                        o--o                                #
#                        o--o      o         o                             #
#                        |   |     |         |  o                          #
#                        O-Oo  o-o O-o  o-o -o-    o-o o-o                 #
#                        |  \  | | |  | | |  |  | |     \                  #
#                        o   o o-o o-o  o-o  o  |  o-o o-o                 #
#                                                                          #
#    Jemison High School - Huntsville Alabama                              #
# ------------------------------------------------------------------------ #

import json
import logging
import os

from wpilib import RobotBase, get_deploy_directory
from wpinet import WebServer

ELASTIC_LAYOUT_FILE = "elastic-layout.json"
ELASTIC_LAYOUT_PORT = 5800

# Setup Logging
logger = logging.getLogger(__name__)


class ElasticDashboardServer:
    """
    The 2027+ version of the Elastic dashboard supports downloading of the dashboard
    from the robot. If robot's 'deploy' directory has a valid elastic layout, automatically
    support it.
    """

    def __init__(self):
        self._elastic_layout_server: WebServer | None = None

    def start(self) -> WebServer | None:
        if self._elastic_layout_server is None:
            # Locate the settings file
            deploy_dir = get_deploy_directory()
            file_path = os.path.join(deploy_dir, ELASTIC_LAYOUT_FILE)
            try:
                with open(file_path) as f:
                    # Just validate the JSON can be parsed
                    _ = json.loads(f.read())

            except FileNotFoundError, ValueError, json.JSONDecodeError:
                logger.exception(f"Failed to load elastic dashboard file: {file_path}")
                return None

            # Now create the server
            try:
                web_server = WebServer.get_instance()
                web_server.start(ELASTIC_LAYOUT_PORT, deploy_dir)
                self._elastic_layout_server = web_server

            except Exception as _e:
                logger.exception("Failed to start elastic dashboard server")
                return None

        return self._elastic_layout_server

    def stop(self) -> None:
        server, self._elastic_layout_server = self._elastic_layout_server, None

        if server is not None:
            try:
                server.stop(ELASTIC_LAYOUT_PORT)

            except Exception as _e:
                logger.exception("Failure during stop of elastic dashboard server")

    def validate_settings_file(self) -> None:
        """
        Call this after all network tables that the dashboard uses are initialized, and
        it will validate the widgets
        """
        if not RobotBase.is_simulation():
            return

        pass  # TODO: This would be a useful item to run during simulation...
