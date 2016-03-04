#!/usr/bin/env python
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
Groups together code used for creating a NuPIC model and dealing with IO.
(This is a component of the One Hot Gym Prediction Tutorial.)
"""
import importlib
import sys
import csv
import datetime
from optparse import OptionParser
from nupic.data.inference_shifter import InferenceShifter
from nupic.frameworks.opf.metrics import MetricSpec
from nupic.frameworks.opf.modelfactory import ModelFactory
from nupic.frameworks.opf.predictionmetricsmanager import MetricsManager
from swarm_description import SWARM_DESCRIPTION
import nupic_output


DESCRIPTION = (
  "Starts a NuPIC model from the model params returned by the swarm\n"
  "and pushes each line of input  into the model. Results\n"
  "are written to an output file (default) or plotted dynamically if\n"
  "the --plot option is specified.\n"
  "NOTE: You must run ./swarm.py before this, because model parameters\n"
  "are required to run NuPIC.\n"
)
DATA_DIR = "."
PREDICTED_FIELD = SWARM_DESCRIPTION["inferenceArgs"]["predictedField"]
NAME = SWARM_DESCRIPTION["streamDef"]["info"]
MODEL_PARAMS_DIR = "./model_params"
# '7/2/10 0:00'
DEFAULT_DATE_FORMAT = "%m/%d/%y %H:%M"

_METRIC_SPECS = (
    MetricSpec(field=PREDICTED_FIELD, metric='multiStep',
               inferenceElement='multiStepBestPredictions',
               params={'errorMetric': 'aae', 'window': 1000, 'steps': 1}),
    MetricSpec(field=PREDICTED_FIELD, metric='trivial',
               inferenceElement='prediction',
               params={'errorMetric': 'aae', 'window': 1000, 'steps': 1}),
    MetricSpec(field=PREDICTED_FIELD, metric='multiStep',
               inferenceElement='multiStepBestPredictions',
               params={'errorMetric': 'altMAPE', 'window': 1000, 'steps': 1}),
    MetricSpec(field=PREDICTED_FIELD, metric='trivial',
               inferenceElement='prediction',
               params={'errorMetric': 'altMAPE', 'window': 1000, 'steps': 1}),
)

parser = OptionParser(
  usage="%prog [options]\n\nSwarm over input file, using swarm_description as parameters."
)
parser.add_option(
    "-p",
    "--plot",
    dest="plot",
    nargs=2,
    default=[],
    help="X and Y axis data to plot dynamically with the prediction during the run.\n"
    "Results will not be saved as a csv file.")
parser.add_option(
    "-d",
    "--date_format",
    dest="date_format",
    default=DEFAULT_DATE_FORMAT,
    help="Format used to read input's timestamp. Default is "+DEFAULT_DATE_FORMAT+".")
parser.add_option(
    "-v",
    "--verbose",
    dest="verbose",
    action="store_true",
    default=True,
    help="Print infos")

def createModel(modelParams):
  model = ModelFactory.create(modelParams)
  model.enableInference({"predictedField": PREDICTED_FIELD})
  return model


def getModelParamsFromName(name):
  importName = "model_params.%s_model_params" % (
    name.replace(" ", "_").replace("-", "_")
  )
  print "Importing model params from %s" % importName
  try:
    importedModelParams = importlib.import_module(importName).MODEL_PARAMS
  except ImportError as error:
    print error
    raise Exception("No model params exist for '%s'. Run swarm first!"
                    % name)
  return importedModelParams


def translate_data(type, value):
    if type == "datetime":
        return datetime.datetime.strptime(value, options.date_format)
    if type == "float":
        return float(value)


def runIoThroughNupic(inputData, model, name, plot):
  inputFile = open(inputData, "rb")
  csvReader = csv.reader(inputFile)
  # skip header rows
  csvReader.next()
  csvReader.next()
  csvReader.next()

  shifter = InferenceShifter()
  if len(plot) == 0:
      for field in SWARM_DESCRIPTION["includedFields"]:
          plot.append(field["fieldName"])
      output = nupic_output.NuPICFileOutput(name, plot)
  else:
      output = nupic_output.NuPICPlotOutput(name, plot)

  metricsManager = MetricsManager(_METRIC_SPECS, model.getFieldInfo(),
                                  model.getInferenceType())

  counter = 0
  for row in csvReader:
    counter += 1
    data = {}
    fldCounter = 0
    for field in SWARM_DESCRIPTION["includedFields"]:
        data[field["fieldName"]] = translate_data(field["fieldType"], row[fldCounter])
        fldCounter += 1
    result = model.run(data)
    result.metrics = metricsManager.update(result)

    if options.verbose is not None and counter % 100 == 0:
      print "Read %i lines..." % counter
      print ("After %i records, 1-step altMAPE=%f" % (counter,
              result.metrics["multiStepBestPredictions:multiStep:"
                             "errorMetric='altMAPE':steps=1:window=1000:"
                             "field="+PREDICTED_FIELD]))

    if plot:
      result = shifter.shift(result)

    prediction = result.inferences["multiStepBestPredictions"][1]
    vals = []
    for field in plot:
        vals.append(data[field])
    output.write(vals, prediction)

  inputFile.close()
  output.close()


if __name__ == "__main__":
  print DESCRIPTION
  (options, args) = parser.parse_args(sys.argv[1:])
  print "Creating model from %s..." % NAME
  model = createModel(getModelParamsFromName(NAME))
  inputData = SWARM_DESCRIPTION["streamDef"]["streams"][0]["source"]
  runIoThroughNupic(inputData, model, NAME, options.plot)
