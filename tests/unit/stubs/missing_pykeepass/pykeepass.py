# Copyright (c) 2023 Black Cockpit LLC <mehdi@black-cockpit.com>
# SPDX-License-Identifier: MIT

# Shadow the pykeepass library with a module that cannot be imported
raise ModuleNotFoundError("No module named 'pykeepass'")
