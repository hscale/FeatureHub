include .env
-include .env.local

.DEFAULT_GOAL=help

.PHONY: help
help:
	@echo "Manage FeatureHub deployment"
	@echo ""
	@echo "Options:"
	@echo "    help: Display this help message."
	@echo "    build: Build images, create network and volumes, install jupyterhub config"
	@echo "    up: Launch the app, creating all necessary containers."
	@echo "    stop: Stop the app, stopping all containers."
	@echo "    start: Restart the app, restarting all containers."
	@echo "    down: Shut down the app, removing all created containers."
	@echo "    clean: Remove all containers, data volumes, user files, and config files."
	@echo "    clean_all: Clean, and additionally remove images and network."

.PHONY: setup_files
setup_files:
	sudo mkdir -p $(FF_DATA_DIR)/config/jupyterhub
	sudo chmod -R 777 $(FF_DATA_DIR)
	sudo chmod 700 $(FF_DATA_DIR)/config/jupyterhub
	sudo cp ./jupyterhub_config.py $(FF_DATA_DIR)/config/jupyterhub/
	sudo cp ./userlist $(FF_DATA_DIR)/config/jupyterhub/ 2>/dev/null || true
	sudo cp ./cull_idle_servers.py $(FF_DATA_DIR)/config/jupyterhub
	sudo cp ../share/static/images/featurehub.png $(FF_DATA_DIR)/config/jupyterhub

.PHONY: teardown_files
teardown_files:
	sudo rm -rf $(FF_DATA_DIR)/{users,config,log}

.PHONY: clean_all
clean_all: clean kill_images kill_network kill_secrets_volume

.PHONY: clean
clean: kill_containers teardown_files kill_db_volumes

.PHONY: kill_containers
kill_containers:
	@docker rm -f $(HUB_CONTAINER_NAME) $(MYSQL_CONTAINER_NAME) $(EVAL_CONTAINER_NAME) 2>/dev/null || echo "No hub/db containers found."
	@docker rm -f $(shell docker ps -a -q --filter name=^/${FF_CONTAINER_NAME}-.*$) 2>/dev/null || echo "No user containers found."

.PHONY: kill_images
kill_images:
	@docker rmi -f $(HUB_IMAGE_NAME) $(FF_IMAGE_NAME) $(EVAL_IMAGE_NAME) 2>/dev/null || echo "No images found."

.PHONY: network
network:
	@docker network inspect $(DOCKER_NETWORK_NAME) >/dev/null 2>&1 || docker network create $(DOCKER_NETWORK_NAME)

.PHONY: kill_network
kill_network:
	@docker network inspect $(DOCKER_NETWORK_NAME) >/dev/null 2>&1 && docker network rm $(DOCKER_NETWORK_NAME) || echo "No network found."

.PHONY: volumes
volumes:
	@docker volume inspect $(MYSQL_DATA_VOLUME_NAME) >/dev/null 2>&1 || docker volume create --name $(MYSQL_DATA_VOLUME_NAME)
	@docker volume inspect $(SECRETS_VOLUME_NAME) >/dev/null 2>&1 || docker volume create --name $(SECRETS_VOLUME_NAME)

.PHONY: kill_db_volumes
kill_db_volumes:
	@docker volume inspect $(MYSQL_DATA_VOLUME_NAME) >/dev/null 2>&1 && docker volume rm $(MYSQL_DATA_VOLUME_NAME) || echo "No volumes found."

.PHONY: kill_secrets_volume
kill_secrets_volume:
	@docker volume inspect $(SECRETS_VOLUME_NAME) >/dev/null 2>&1 && docker volume rm $(SECRETS_VOLUME_NAME) || echo "No volumes found."

.PHONY: build
build: build_static build_services

.PHONY: build_static
build_static: network setup_files
	@{\
	    export $(shell tr '\n' ' ' < .env.local);\
	    docker-compose -p $(FF_PROJECT_NAME) -f docker-compose-static.yml build;\
	}

.PHONY: build_services
build_services: network volumes setup_files
	@{\
	    export $(shell tr '\n' ' ' < .env.local);\
	    docker-compose -p $(FF_PROJECT_NAME) -f docker-compose.yml build;\
        }

.PHONY: ssl
ssl:
	./gen_ssl.sh

.PHONY: up
up:
	@{\
	    export $(shell tr '\n' ' ' < .env.local);\
	    docker-compose -p $(FF_PROJECT_NAME) -f docker-compose.yml up -d;\
	}

.PHONY: stop
stop:
	@{\
	    export $(shell tr '\n' ' ' < .env.local);\
	    docker-compose -p $(FF_PROJECT_NAME) -f docker-compose.yml stop;\
	}

.PHONY: start
start:
	@{\
	    export $(shell tr '\n' ' ' < .env.local);\
	    docker-compose -p $(FF_PROJECT_NAME) -f docker-compose.yml start;\
	}

.PHONY: down
down:
	@{\
	    export $(shell tr '\n' ' ' < .env.local);\
	    docker-compose -p $(FF_PROJECT_NAME) -f docker-compose.yml down;\
	}

.PHONY: monitor_start
monitor_start:
	sudo ./monitor.py start &

.PHONY: monitor_delete
monitor_delete:
	sudo ./monitor.py delete

.PHONY: monitor_stop
monitor_stop:
	sudo ./monitor.py stop

# Driver for rebuild_eval
.PHONY: remove_eval
remove_eval:
	docker rm -f $(EVAL_CONTAINER_NAME)

.PHONY: rebuild_eval
rebuild_eval: build remove_eval up
