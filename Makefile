.PHONY: build-PageMonitorFunction

build-PageMonitorFunction:
	cp -R pagemonitor "$(ARTIFACTS_DIR)/"
	cp -R lambda "$(ARTIFACTS_DIR)/"
	cp requirements.txt "$(ARTIFACTS_DIR)/"
