# encoding: utf-8
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Contact: Kyle Lahnakoski (kyle@lahnakoski.com)
#
import gc
from math import floor, log

from mo_logs import Log
from mo_math.randoms import Random
from mo_times import Timer

from mo_dots import Data, to_data
from mo_dots.lists import FlatList


def baseline(v):
    return [v]


NUM_INPUT = 1000 * 1000
NUM_REPEAT = 3


def test_wrap_1():
    Log.alert("Random structs")
    switch = [
        lambda: Data(i=Random.int(2000)),
        lambda: {"i": Random.int(2000)},
        lambda: FlatList([{"i": Random.int(2000)}]),
        lambda: [{"i": Random.int(2000)}],
    ]

    inputs = [switch[min(len(switch) - 1, int(floor(-log(Random.float(), 2))))]() for i in range(NUM_INPUT)]

    for i in range(NUM_REPEAT):
        results = []
        gc.collect()
        with Timer("more struct: to_data"):
            for v in inputs:
                results.append(to_data(v))

        results = []
        gc.collect()
        with Timer("more struct: baseline"):
            for v in inputs:
                results.append(baseline(v))

        Log.info("Done {{i}} of {{num}}", i=i, num=NUM_REPEAT)


def test_wrap_2():
    Log.alert("Random types")
    switch = [
        lambda: Random.int(20),
        lambda: Random.string(20),
        lambda: {"i": Random.int(2000)},
        lambda: Data(i=Random.int(2000)),
        lambda: FlatList([{"i": Random.int(2000)}]),
        lambda: [{"i": Random.int(2000)}],
    ]

    inputs = [switch[min(len(switch) - 1, int(floor(-log(Random.float(), 2))))]() for i in range(NUM_INPUT)]

    for i in range(NUM_REPEAT):
        results = []
        gc.collect()
        with Timer("more string: to_data"):
            for v in inputs:
                results.append(to_data(v))

        results = []
        gc.collect()
        with Timer("more string: baseline"):
            for v in inputs:
                results.append(baseline(v))

        Log.info("Done {{i}} of {{num}}", i=i, num=NUM_REPEAT)


test_wrap_1()
test_wrap_2()
