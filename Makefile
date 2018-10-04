
PLUGIN_NAME=plugin.video.polonium210
PLUGIN_VERSION=0.3.1
REPO_NAME=repository.polonium-210
REPO_VERSION=1.0.0

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

plugin-zip:
	zip -0 -r zips/${PLUGIN_NAME}/${PLUGIN_NAME}-${PLUGIN_VERSION}.zip ${PLUGIN_NAME}/

plugin-zip-set-latest:
	ln -s zips/${PLUGIN_NAME}/${PLUGIN_NAME}-${PLUGIN_VERSION}.zip zips/${PLUGIN_NAME}-latest.zip

plugin-zip-latest: plugin-zip plugin-zip-set-latest

repo-zip:
	zip -0 -r zips/${REPO_NAME}/${REPO_NAME}-${REPO_VERSION}.zip ${REPO_NAME}/

repo-zip-set-latest:
	ln -s zips/${REPO_NAME}/${REPO_NAME}-${REPO_VERSION}.zip zips/${REPO_NAME}-latest.zip 

repo-zip-latest: repo-zip repo-zip-set-latest

addons-md5:
	md5sum addons.xml > addons.xml.md5
