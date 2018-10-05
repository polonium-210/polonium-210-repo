
PLUGIN_NAME=plugin.video.polonium210
PLUGIN_VERSION=0.3.1
REPO_NAME=repository.polonium-210
REPO_VERSION=1.1.0

default:
	@echo ""
	@echo "Targets:"
	@echo ""
	@echo "  info                   Print build info"
	@echo "  md5                    Create md5 hash file"
	@echo ""

info:
	@echo "Plugin ${PLUGIN_NAME} version: ${PLUGIN_VERSION}"
	@echo "Repository ${REPO_NAME} version: ${REPO_VERSION}"
	@echo "Deployment addons path: ${DEPLOY_ADDONS_PATH}"

plugin-zip:
	zip -0 -r zips/${PLUGIN_NAME}/${PLUGIN_NAME}-${PLUGIN_VERSION}.zip ${PLUGIN_NAME}/

plugin-zip-md5:
	md5sum zips/${PLUGIN_NAME}/${PLUGIN_NAME}-${PLUGIN_VERSION}.zip > zips/${PLUGIN_NAME}/${PLUGIN_NAME}-${PLUGIN_VERSION}.zip.md5

plugin-zip-set-latest:
	ln -s zips/${PLUGIN_NAME}/${PLUGIN_NAME}-${PLUGIN_VERSION}.zip zips/${PLUGIN_NAME}-latest.zip

plugin-zip-latest: plugin-zip plugin-zip-md5 plugin-zip-set-latest

repo-zip:
	zip -0 -r zips/${REPO_NAME}/${REPO_NAME}-${REPO_VERSION}.zip ${REPO_NAME}/

repo-zip-md5:
	md5sum zips/${REPO_NAME}/${REPO_NAME}-${REPO_VERSION}.zip > zips/${REPO_NAME}/${REPO_NAME}-${REPO_VERSION}.zip.md5

repo-zip-set-latest:
	ln -s zips/${REPO_NAME}/${REPO_NAME}-${REPO_VERSION}.zip zips/${REPO_NAME}-latest.zip 

repo-zip-latest: repo-zip repo-zip-md5 repo-zip-set-latest

addons-md5:
	md5sum addons.xml > addons.xml.md5

clean-deploy:
	rm -rf '${DEPLOY_ADDONS_PATH}/${PLUGIN_NAME}'

copy-deploy:
	cp -R ${PLUGIN_NAME} '${DEPLOY_ADDONS_PATH}/${PLUGIN_NAME}'

deploy: clean-deploy copy-deploy
