# encoding: utf-8
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at https://www.mozilla.org/en-US/MPL/2.0/.
#
# Contact: Kyle Lahnakoski (kyle@lahnakoski.com)
#
import mo_dots
from mo_dots import Data

d = Data(a=42)
# C ACCELERATOR MUST BE ACTIVE; A FAILED COMPILE IS A BROKEN INSTALL HERE
assert type(mo_dots.to_data).__name__ == "builtin_function_or_method"
