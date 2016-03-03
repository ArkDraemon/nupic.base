# ----------------------------------------------------------------------
# Numenta Platform for Intelligent Computing (NuPIC)
# Copyright (C) 2013, Numenta, Inc.  Unless you have an agreement
# with Numenta, Inc., for a separate license for this software code, the
# following terms and conditions apply:
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero Public License version 3 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU Affero Public License for more details.
#
# You should have received a copy of the GNU Affero Public License
# along with this program.  If not, see http://www.gnu.org/licenses.
#
# http://numenta.org/licenses/
# ----------------------------------------------------------------------
"""
Provides two classes with the same signature for writing data out of NuPIC
models.
(This is a component of the One Hot Gym Prediction Tutorial.)
"""
import csv
from collections import deque
from abc import ABCMeta, abstractmethod
# Try to import matplotlib, but we don't have to.
import matplotlib
matplotlib.use('TKAgg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.dates import date2num

WINDOW = 100


class NuPICOutput(object):

  __metaclass__ = ABCMeta


  def __init__(self, name, headers, showAnomalyScore=False):
    self.name = name
    self.headers = headers
    self.showAnomalyScore = showAnomalyScore


  @abstractmethod
  def write(self, columns, predictedValue,
            predictionStep=1):
    pass


  @abstractmethod
  def close(self):
    pass


class NuPICFileOutput(NuPICOutput):

    def __init__(self, *args, **kwargs):
        super(NuPICFileOutput, self).__init__(*args, **kwargs)
        self.outputFile = ""
        self.outputWriter = ""
        self.lineCount = 0
        outputFileName = "%s_out.csv" % self.name
        print "Preparing to output %s data to %s" % (self.name, outputFileName)
        self.outputFile = open(outputFileName, "w")
        self.outputWriter = csv.writer(self.outputFile)
        self.outputWriter.writerow(self.headers)

    def write(self, columns, predictedValue,
            predictionStep=1):
        self.outputWriter.writerow(columns + [predictedValue])
        self.lineCount += 1

    def close(self):
        self.outputFile.close()
        print "Done. Wrote %i data lines to %s." % (self.lineCount, self.name)


class NuPICPlotOutput(NuPICOutput):

    def __init__(self, *args, **kwargs):
        super(NuPICPlotOutput, self).__init__(*args, **kwargs)
        # Turn matplotlib interactive mode on.
        plt.ion()
        self.date = ""
        self.convertedDate = ""
        self.actualValue = ""
        self.predictedValue = ""
        self.actualLine = ""
        self.predictedLine = ""
        self.linesInitialized = False
        self.graph = []
        fig = plt.figure(figsize=(14, 6))
        gs = gridspec.GridSpec(1, 1)
        self.graph = fig.add_subplot(gs[0, 0])
        plt.title(self.name)
        plt.ylabel(self.headers[0])
        plt.xlabel(self.headers[1])
        plt.tight_layout()

    def initializeLines(self, timestamps):
        print "initializing %s" % self.name
        self.date = deque([timestamps] * WINDOW, maxlen=WINDOW)
        self.convertedDates = deque([date2num(self.date)], maxlen=WINDOW)
        self.actualValue = deque([0.0] * WINDOW, maxlen=WINDOW)
        self.predictedValue = deque([0.0] * WINDOW, maxlen=WINDOW)
        self.actualLine, = self.graph.plot(self.date, self.actualValue)
        self.predictedLine, = self.graph.plot(self.date, self.predictedValue)
        self.linesInitialized = True

    def write(self, columns, predictedValues, predictionStep=1):
        timestamps = columns[0]
        actual_values = columns[1]
        # We need the first timestamp to initialize the lines at the right X value,
        # so do that check first.
        if not self.linesInitialized:
            self.initializeLines(timestamps)

        self.date.append(timestamps)
        self.convertedDates.append(date2num(timestamps))
        self.actualValue.append(actual_values)
        self.predictedValue.append(predictedValues)

        # Update data
        self.actualLine.set_xdata(self.convertedDates)
        self.actualLine.set_ydata(self.actualValue)
        self.predictedLine.set_xdata(self.convertedDates)
        self.predictedLine.set_ydata(self.predictedValue)

        self.graph.relim()
        self.graph.autoscale_view(True, True, True)

        plt.draw()
        plt.legend(('actual', 'predicted'), loc=3)
        plt.pause(0.00000001)

    def close(self):
        plt.ioff()
        plt.show()


NuPICOutput.register(NuPICFileOutput)
NuPICOutput.register(NuPICPlotOutput)
