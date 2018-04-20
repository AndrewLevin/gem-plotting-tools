#!/bin/env python

if __name__ == '__main__':
    """
    Takes a list of scandates file, see parseListOfScanDatesFile(...) documentation,
    and launches a job for each (chamberName, scandate) pair.  Each job will 
    launch anaUltraScurve.py
    """
    
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option("--anaType", type="string", dest="anaType",
                      help="Analysis type to be executed, from list {'scurve','trim'}", metavar="anaType")
    parser.add_option("--calFile", type="string", dest="calFile", default=None,
                      help="File specifying CAL_DAC/VCAL to fC equations per VFAT",
                      metavar="calFile")
    parser.add_option("-c","--channels", action="store_true", dest="channels",
                      help="Make plots vs channels instead of strips", metavar="channels")
    parser.add_option("-d", "--debug", action="store_true", dest="debug",
                      help="print extra debugging information", metavar="debug")
    parser.add_option("--extChanMapping", type="string", dest="extChanMapping", default=None,
                      help="Physical filename of a custom, non-default, channel mapping (optional)", metavar="extChanMapping")
    parser.add_option("-f", "--fit", action="store_true", dest="performFit",
                      help="Fit scurves and save fit information to output TFile", metavar="performFit")
    parser.add_option("-i", "--infilename", type="string", dest="filename",
                      help="Tab delimited file specifying chamber name and scandates to analyze", metavar="filename")
    parser.add_option("-p","--panasonic", action="store_true", dest="PanPin",
                      help="Make plots vs Panasonic pins instead of strips", metavar="PanPin")
    parser.add_option("-q","--queue", type="string", dest="queue", default="8nm",
                        help="queue to submit your jobs to", metavar="queue")
    parser.add_option("-t", "--type", type="string", dest="GEBtype", default="long",
                      help="Specify GEB (long/short)", metavar="GEBtype")
    parser.add_option("--zscore", type="float", dest="zscore", default=3.5,
                      help="Z-Score for Outlier Identification in MAD Algo", metavar="zscore")
    parser.add_option("--ztrim", type="float", dest="ztrim", default=4.0,
                      help="Specify the p value of the trim", metavar="ztrim")
    
    parser.set_defaults(filename="listOfScanDates.txt")
    (options, args) = parser.parse_args()
    
    # Check if the queue is supported
    # See: https://cern.service-now.com/service-portal/article.do?n=KB0000470
    import os
    from anaInfo import queueNames, tree_names
    if options.queue not in queueNames:
        print("queue '%s' not understood"%options.queue)
        print("list of supported queues is:", queueNames)
        exit(os.EX_USAGE)
        pass

    # Check anaType is understood
    supportedAnaTypes = ['scurve','trim']
    if options.anaType not in supportedAnaTypes:
        print("Invalid analysis specificed, please select only from the list:")
        print(supportedAnaTypes)
        exit(os.EX_USAGE)
        pass

    # Prepare the commands for making the
    from gempython.utils.wrappers import envCheck, runCommand
    envCheck('DATA_PATH')
    envCheck('BUILD_HOME')
    #envCheck('ELOG_PATH')

    dataPath = os.getenv('DATA_PATH')
    buildHome= os.getenv('BUILD_HOME')

    # Get info from input file
    from anautilities import getDirByAnaType, filePathExists, parseListOfScanDatesFile
    parsedTuple = parseListOfScanDatesFile(options.filename, alphaLabels=True)
    listChamberAndScanDate = parsedTuple[0]

    # Setup output scandates list
    outputScanDatesName = options.filename.strip('.txt')
    outputScanDatesName += "_Input4GemPlotter.txt"
    outputScanDatesFile = open(outputScanDatesName, 'w+')
    outputScanDatesFile.write('ChamberName\tscandate\n')

    # Make and launch a job for each file
    import time
    for idx,chamberAndScanDatePair in enumerate(listChamberAndScanDate):
        # Setup the path
        dirPath = getDirByAnaType(options.anaType, chamberAndScanDatePair[0], options.ztrim)
        dirPath = "%s/%s"%(dirPath,chamberAndScanDatePair[1])

        # Check if file exists, if it does not write to output as commented line but skip to next input
        if not filePathExists(dirPath, tree_names[options.anaType][0]):
            outputScanDatesFile.write('#%s\t%s'%(chamberAndScanDatePair[0],chamberAndScanDatePair[1]))
            continue
        outputScanDatesFile.write('%s\t%s'%(chamberAndScanDatePair[0],chamberAndScanDatePair[1]))

        # Input file
        jobInputFile = "%s/%s"%(dirPath, tree_names[options.anaType][0])
        
        # stdout
        jobStdOut = "%s/stdout"%dirPath
        runCommand( ["mkdir","-p", jobStdOut ] )

        # stderr
        jobStdErr = "%s/stderr"%dirPath
        runCommand( ["mkdir","-p", jobStdErr ] )

        # script to be run by the cluster
        jobScriptName = "%s/clusterJob.sh"%dirPath
        jobScript = open(jobScriptName, 'w+')
        jobScript.write('#!/bin/zsh\n')
        jobScript.write('export BUILD_HOME=%s\n'%buildHome)
        #jobScript.write('export DATA_PATH=%s'%dataPath)
        jobScript.write('source %s/cmsgemos/setup/paths.sh\n'%buildHome)
        jobScript.write('source %s/gem-plotting-tools/setup/paths.sh\n'%buildHome)

        # make the python command
        pythonCmd = 'anaUltraScurve.py -i %s -t %s --zscore=%f --ztrim=%f'%(
                jobInputFile,
                options.GEBtype,
                options.zscore,
                options.ztrim)
        if options.calFile is not None:
            pythonCmd += ' --calFile=%s'%(options.calFile)
            pass
        if options.channels:
            pythonCmd += ' --channels'
            pass
        if options.extChanMapping is not None:
            pythonCmd += ' --extChanMapping=%s'%(options.extChanMapping)
            pass
        if options.performFit:
            pythonCmd += ' --fit'
            pass
        if options.PanPin:
            pythonCmd += ' --panasonic'
            pass
        pythonCmd += '\n'
        
        jobScript.write(pythonCmd)
        jobScript.close()
        runCommand( ['chmod', '+x', jobScriptName] )

        jobCmd = [
                'bsub',
                '-q',
                options.queue,
                '-o',
                jobStdOut,
                '-e',
                jobStdErr,
                jobScriptName ]

        if options.debug:
            print(idx, jobCmd)
            pass
        else:
            runCommand(jobCmd)
            time.sleep(1)
            pass
        pass # end loop over listChamberAndScanDate

    print("Job submission completed")
    print("To check the status of your jobs execute:")
    print("")
    print("\tbjos")
    print("")
    print("To kill a running job execute:")
    print("")
    print("\tbkill JOBID")
    print("")
    print("Here JOBID is the number returned when calling 'bjobs'")
    print("")
    print("To force kill a running job call:")
    print("\tbkill -r JOBID")
    print("")
    print("For additional information see: https://batchconf.web.cern.ch/batchconf/doc/lsf/print/lsf_users_guide.pdf")
    print("")
    print("Finally for a time series output of the data call:")
    print("")
    print("\tgemPlotter.py --infilename=%s --anaType=scurveAna --branchName=threshold --make2D --alphaLabels -c -a --axisMax=10")
    print("\tgemPlotter.py --infilename=%s --anaType=scurveAna --branchName=noise --make2D --alphaLabels -c -a --axisMax=2")
    print("\tgemPlotter.py --infilename=%s --anaType=scurveAna --branchName=ped_eff --make2D --alphaLabels -c -a --axisMax=1")
    print("\tgemPlotter.py --infilename=%s --anaType=scurveAna --branchName=mask --make2D --alphaLabels -c -a --axisMax=1")
    print("\tgemPlotter.py --infilename=%s --anaType=scurveAna --branchName=maskReason --make2D --alphaLabels -c -a --axisMax=1")
