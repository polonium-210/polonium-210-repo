NAME=repository.polonium-210
VERSION=1.0.0

default:
	@echo ""
	@echo "Targets:"
	@echo ""
	@echo "  params                 Print build parameter"
	@echo "  md5                    Create md5 hash file"
	@echo ""

params:
	@echo "Version: ${VERSION}"

md5:
	md5sum addons.xml > addons.xml.md5
