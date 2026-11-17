.PHONY: test install uninstall cache-rebuild cache-stats system-rebuild system-stats help

help:
	@printf 'Targets: test install uninstall cache-rebuild cache-stats system-rebuild system-stats help\n'

test:
	@bash tests/run_all.sh

install:
	@bash install.sh

uninstall:
	@bash uninstall.sh

cache-rebuild:
	@bash autocorrect.sh cache rebuild

cache-stats:
	@bash autocorrect.sh cache stats

system-rebuild:
	@bash autocorrect.sh system rebuild

system-stats:
	@bash autocorrect.sh system stats
