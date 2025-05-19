import docker
import schedule
import time
import logging

from config import Cfg
from gateway import get_feature_data


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s",
                    handlers=[logging.StreamHandler()])  # Logs to stdout

client = docker.from_env()


AI_FEATURES = ["HM01", "HM02", "HM03", "HM05", "HM07", "MHE01", "MHE03", "MHE04", "MHE07", "MHE08", "MHE09", "MHE10",
               "OTH02", "PAR01", "PAR02", "PAR03","PL03", "PL02", "PPE01", "PPE02", "PRD01", "TCOUNT", "VEH01", "VEH02", "VEH03"]
AI_DEEPSTREAM = ["deepstream-pipeline", "ds_alcohol_person"]


def is_relevant_container(container):
    container_networks = container.attrs['NetworkSettings']['Networks'].keys()
    project_label = container.labels.get('com.docker.compose.project')
    return Cfg.network_name in container_networks or project_label == Cfg.project_name


def get_service_status(service_name):
    """
    Get the status of AI feature from the database
    """
    try:
        data = get_feature_data(service_name)

        if data is None:
            return None

        status = bool(data.get('status'))
        return status
    except Exception as e:
        logging.error(f"Error querying database: {e}")
        return None


# check health of containers and restart if unhealthy
def check_and_restart_containers():
    """
    Check the health of containers and restart if unhealthy
    """
    logging.info("Checking container health...")
    containers = client.containers.list()
    for container in containers:
        if is_relevant_container(container):
            service_name = container.labels.get('com.docker.compose.service')
            if service_name not in AI_DEEPSTREAM:
                continue

            health = container.attrs['State'].get('Health')
            if health and health['Status'] == 'unhealthy':
                logging.warning(f"Restarting unhealthy container: {container.name}")
                container.restart()
    logging.info("Container health check complete.")

# manage services based on DB status
def manage_services_based_on_db():
    """
    Check the status of AI features in the database and start/stop the corresponding
    """
    containers = client.containers.list()
    logging.info("Checking DB status for services...")
    for container in containers:
        if is_relevant_container(container):
            service_name = container.labels.get('com.docker.compose.service')
            service_name = service_name.upper()
            if service_name not in AI_FEATURES:
                continue

            status_in_db = get_service_status(service_name)
            if status_in_db is None:
                continue

            if not status_in_db and container.status == "running":
                logging.warning(f"Stopping container based on DB status: {service_name}")
                container.stop()
            elif status_in_db and container.status != "running":
                logging.info(f"Starting container based on DB status: {service_name}")
                container.start()

    logging.info("DB status check complete.")

# schedule tasks
schedule.every(Cfg.check_health_interval).seconds.do(check_and_restart_containers)
schedule.every(Cfg.check_db_status_interval).seconds.do(manage_services_based_on_db)

if __name__ == "__main__":
    while True:
        schedule.run_pending()
        time.sleep(60)