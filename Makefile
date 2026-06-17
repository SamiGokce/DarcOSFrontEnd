PROFILE := profiles/darcos
OUT     := out
WORK    := work

.PHONY: build build-container clean test setup validate help

help:
	@echo "DarcOS — custom Arch Linux distribution"
	@echo ""
	@echo "Targets:"
	@echo "  setup            Install dev dependencies (Arch host)"
	@echo "  validate         Check profile structure"
	@echo "  test             Run validation tests"
	@echo "  build            Build live ISO on Arch (requires root + archiso)"
	@echo "  build-container  Build ISO via Docker/Podman (Fedora, Ubuntu, etc.)"
	@echo "  clean            Remove build artifacts"

setup:
	@bash scripts/setup-dev.sh

validate:
	@bash src/__tests__/validate-profile.sh

test: validate
	@command -v bats >/dev/null 2>&1 && bats src/__tests__/profile.bats || bash src/__tests__/validate-profile.sh

build:
	@sudo bash scripts/build.sh

build-container:
	@bash scripts/build-container.sh

clean:
	@rm -rf $(WORK) $(OUT)
	@echo "Cleaned $(WORK) and $(OUT)"
