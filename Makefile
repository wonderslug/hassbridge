.PHONY: help update-libs

PYENV := $(shell command -v pyenv 2> /dev/null)
NAME?=indigo-hassbridge
PYTHON_VERSION=2.7.10

PLUGIN=HassBridge.indigoPlugin
PLUGIN_ROOT=$(PLUGIN)/Contents/Server\ Plugin
REQUIREMENT_FILE=$(PLUGIN_ROOT)/requirements.txt
LIBS_DIR=$(PLUGIN_ROOT)/libs

RELEASE_VERSION=0.2.2
RELEASE_DIR=release
RELEASE_NAME=$(PLUGIN)-$(RELEASE_VERSION)
RELEASE_PACKAGE_PATH=$(RELEASE_DIR)/$(RELEASE_NAME).zip


target:
	$(info ${HELP_MESSAGE})
	@exit 0

# Make sure that pyenv is configured properly and that we can use it in our setup target.
validation:
ifndef PYENV
    $(error "make sure pyenv is accessible in your path, (usually by adding to PATH variable in bash_profile, zshrc, or other locations based on your platform) See: https://github.com/pyenv/pyenv#installation for the installation insructions.")
endif
ifndef PYENV_SHELL
	$(error "Add 'pyenv init' to your shell to enable shims and autocompletion, (usually by adding to your bash_profile, zshrc, or other locations based on your platform)")
endif
ifndef PYENV_VIRTUALENV_INIT
	$(error "Add 'pyenv virtualenv-init' to your shell to enable shims and autocompletion, (usually by adding to your bash_profile, zshrc, or other locations based on your platform)")
endif

setup: validation
	$(info [*] Download and install python $(PYTHON_VERSION)...)
	@pyenv install $(PYTHON_VERSION)
	@pyenv local $(PYTHON_VERSION)
	$(info [*] Create virtualenv $(NAME) using python $(PYTHON_VERSION)...)
	@pyenv virtualenv $(PYTHON_VERSION) $(NAME)
	@$(MAKE) activate

activate:
	$(info [*] Activate virtualenv $(NAME)...)
	$(shell eval "$$(pyenv init -)" && eval "$$(pyenv virtualenv-init -)" && pyenv activate $(NAME) && pyenv local $(NAME))

update: activate
	rm -rf $(LIBS_DIR)
	mkdir -p $(LIBS_DIR)
	python -m pip install --upgrade -r $(REQUIREMENT_FILE) -t $(LIBS_DIR)
	rm -rf $(LIBS_DIR)/*.dist-info $(LIBS_DIR)/bin

package:
	mkdir -p $(RELEASE_DIR)
	zip -r $(RELEASE_PACKAGE_PATH) $(PLUGIN) -x "*.DS_Store"

clean:
	rm -rf $(RELEASE_DIR)

define HELP_MESSAGE

Usage: $ make [TARGETS]

TARGETS
	install     Install pyenv using the pyenv-installer.
	setup       Download, install and activate a virtualenv for this project.
	activate    Activate the virtual environment for this project.
	init        Initialize and install the requirements and dev-requirements for this project.
	update		update the libs
	package		create a release package

endef