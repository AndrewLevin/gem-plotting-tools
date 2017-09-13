#!/bin/env python

# -*- coding: utf-8 -*-
"""

@author: Anastasia and Cameron Bravo (c.bravo@cern.ch)
         Brian Dorney (brian.l.dorney@cern.ch)

"""
import numpy as np
import os

from anaoptions import parser
from array import array
from gempython.utils.nesteddict import nesteddict as ndict

parser.add_option("-f", "--fit", action="store_true", dest="performFit",
                  help="Fit the latency distributions", metavar="performFit")
parser.add_option("--latSigRange", type="string", dest="latSigRange", default=None,
                  help="Comma separated pair of values defining expected signal range, e.g. lat #epsilon [41,43] is signal", metavar="latSigRange")
parser.add_option("--latNoiseRange", type="string", dest="latNoiseRange", default=None,
                  help="Comma separated pair of values defining expected noise range, e.g. lat #notepsilon [40,44] is noise (lat < 40 || lat > 44)", 
                  metavar="latNoiseRange")

parser.set_defaults(outfilename="latencyAna.root")

(options, args) = parser.parse_args()
filename = options.filename[:-5]
os.system("mkdir " + filename)

print filename
outputfilename = options.outfilename

import ROOT as r
r.gROOT.SetBatch(True)
r.gStyle.SetOptStat(1111111)
inF = r.TFile(filename+'.root',"READ")

#Initializing Histograms
print 'Initializing Histograms'
dict_hVFATHitsVsLat = ndict()
for vfat in range(0,24):
    dict_hVFATHitsVsLat[vfat]   = r.TH1F("vfat%iHitsVsLat"%vfat,"vfat%i"%vfat,256,-0.5,255.5)
    pass

#Filling Histograms
print 'Filling Histograms'
latMin = 1000
latMax = -1
nTrig = -1
for event in inF.latTree:
    dict_hVFATHitsVsLat[int(event.vfatN)].Fill(event.lat,event.Nhits)
    if event.lat < latMin and event.Nhits > 0:
        latMin = event.lat
        pass
    elif event.lat > latMax:
        latMax = event.lat
        pass

    if nTrig < 0:
        nTrig = event.Nev
        pass
    pass

# Set Latency Fitting Bounds - Signal
latFitMin_Sig = latMin
latFitMax_Sig = latMax
if options.latSigRange is not None:
    listLatValues = map(lambda val: float(val), options.latSigRange.split(","))
    if len(listLatValues) != 2:
        print "You must specify exactly two values for determining the latency signal range"
        print "I was given:", listLatValues
        print "Please cross-check"
        exit(os.EX_USAGE)
    else: 
        latFitMin_Sig = min(listLatValues)
        latFitMax_Sig = max(listLatValues)

# Set Latency Fitting Bounds - Noise
latFitMin_Noise = latFitMin_Sig - 1
latFitMax_Noise = latFitMax_Sig + 1
if options.latNoiseRange is not None:
    listLatValues = map(lambda val: float(val), options.latNoiseRange.split(","))
    if len(listLatValues) != 2:
        print "You must specify exactly two values for determining the latency noise range"
        print "I was given:", listLatValues
        print "Please cross-check"
        exit(os.EX_USAGE)
    else: 
        latFitMin_Noise = min(listLatValues)
        latFitMax_Noise = max(listLatValues)

#Make output plots
from math import sqrt
outF = r.TFile(filename+"/"+options.outfilename,"RECREATE")
dict_grNHitsVFAT = ndict()
dict_fitNHitsVFAT_Sig = ndict()
dict_fitNHitsVFAT_Noise = ndict()
grNMaxLatBinByVFAT = r.TGraphErrors(len(dict_hVFATHitsVsLat))
grMaxLatBinByVFAT = r.TGraphErrors(len(dict_hVFATHitsVsLat))
grVFATSigOverBkg = r.TGraphErrors(len(dict_hVFATHitsVsLat))
grVFATNSignalNoBkg = r.TGraphErrors(len(dict_hVFATHitsVsLat))
r.gStyle.SetOptStat(0)
canv_Summary = r.TCanvas("canv_Summary","Latency Summary",500*8,500*3)
canv_Summary.Divide(8,3)
if options.debug and options.performFit:
    print "VFAT\tSignalHits\tSignal/Noise"
for vfat in dict_hVFATHitsVsLat:
    #Store Max Info
    NMaxLatBin = dict_hVFATHitsVsLat[vfat].GetBinContent(dict_hVFATHitsVsLat[vfat].GetMaximumBin())
    grNMaxLatBinByVFAT.SetPoint(vfat, vfat, NMaxLatBin)
    grNMaxLatBinByVFAT.SetPointError(vfat, 0, sqrt(NMaxLatBin))

    grMaxLatBinByVFAT.SetPoint(vfat, vfat, dict_hVFATHitsVsLat[vfat].GetBinCenter(dict_hVFATHitsVsLat[vfat].GetMaximumBin()))
    grMaxLatBinByVFAT.SetPointError(vfat, 0, 0.5) #could be improved upon

    #Initialize
    dict_fitNHitsVFAT_Sig[vfat] = r.TF1("func_N_vs_Lat_VFAT%i_Sig"%vfat,"[0]",latFitMin_Sig,latFitMax_Sig)
    dict_fitNHitsVFAT_Noise[vfat] = r.TF1("func_N_vs_Lat_VFAT%i_Noise"%vfat,"[0]",latMin,latMax)
    dict_grNHitsVFAT[vfat] = r.TGraphAsymmErrors(dict_hVFATHitsVsLat[vfat])
    dict_grNHitsVFAT[vfat].SetName("g_N_vs_Lat_VFAT%i"%vfat)
    
    #Fitting
    if options.performFit:
        # Fit Signal
        dict_fitNHitsVFAT_Sig[vfat].SetParameter(0, NMaxLatBin)
        dict_grNHitsVFAT[vfat].Fit(dict_fitNHitsVFAT_Sig[vfat],"QR")
        #dict_hVFATHitsVsLat[vfat].Fit(dict_fitNHitsVFAT_Sig[vfat],"QR")

        # Remove Signal Region
        latVal = r.Double()
        hitVal = r.Double()
        gTempDist = dict_grNHitsVFAT[vfat].Clone("g_N_vs_Lat_VFAT%i_NoSig"%vfat)
        for idx in range(dict_grNHitsVFAT[vfat].GetN()-1,0,-1):
            gTempDist.GetPoint(idx,latVal,hitVal)
            if latFitMin_Noise < latVal and latVal < latFitMax_Noise:
                gTempDist.RemovePoint(idx)

        # Fit Noise
        dict_fitNHitsVFAT_Noise[vfat].SetParameter(0, 0.)
        gTempDist.Fit(dict_fitNHitsVFAT_Noise[vfat],"QR")

        # Calc Signal & Signal/Noise
        N_Bkg = dict_fitNHitsVFAT_Noise[vfat].GetParameter(0)
        N_Bkg_Err = dict_fitNHitsVFAT_Noise[vfat].GetParError(0)
        N_Sig = dict_fitNHitsVFAT_Sig[vfat].GetParameter(0) - N_Bkg
        N_Sig_Err = sqrt( (dict_fitNHitsVFAT_Sig[vfat].GetParError(0))**2 + N_Bkg_Err**2)

        Sig_Over_Bkg_Err = sqrt( (N_Sig_Err / N_Bkg)**2 + (N_Bkg_Err**2 * (N_Sig / N_Bkg**2)**2) )

        # Add to Plot
        grVFATSigOverBkg.SetPoint(vfat, vfat, N_Sig / N_Bkg )
        grVFATSigOverBkg.SetPointError(vfat, 0, Sig_Over_Bkg_Err)

        grVFATNSignalNoBkg.SetPoint(vfat, vfat, N_Sig )
        grVFATNSignalNoBkg.SetPointError(vfat, 0, N_Sig_Err )

        # Print if requested
        if options.debug:
            print "%i\t%f\t%f"%(vfat, N_Sig, N_Sig / N_Bkg)
        pass

    #Draw
    r.gStyle.SetOptStat(0)
    canv_Summary.cd(vfat+1)
    dict_grNHitsVFAT[vfat].SetMarkerStyle(21)
    dict_grNHitsVFAT[vfat].SetMarkerSize(0.7)
    dict_grNHitsVFAT[vfat].SetLineWidth(2)
    dict_grNHitsVFAT[vfat].GetXaxis().SetRangeUser(latMin, latMax)
    dict_grNHitsVFAT[vfat].GetXaxis().SetTitle("Lat")
    dict_grNHitsVFAT[vfat].GetYaxis().SetTitle("N")
    dict_grNHitsVFAT[vfat].Draw("APE1")
    if options.performFit:
        dict_fitNHitsVFAT_Sig[vfat].SetLineColor(r.kGreen+1)
        dict_fitNHitsVFAT_Sig[vfat].Draw("same")
        dict_fitNHitsVFAT_Noise[vfat].SetLineColor(r.kRed+1)
        dict_fitNHitsVFAT_Noise[vfat].Draw("same")

    #Write
    dirVFAT = outF.mkdir("VFAT%i"%vfat)
    dirVFAT.cd()
    dict_grNHitsVFAT[vfat].Write()
    dict_hVFATHitsVsLat[vfat].Write()
    if options.performFit:
        dict_fitNHitsVFAT_Sig[vfat].Write()
        dict_fitNHitsVFAT_Noise[vfat].Write()
    pass

#Store - Summary
canv_Summary.SaveAs(filename+'/Summary.png')

#Store - Sig Over Bkg
if options.performFit:
    canv_SigOverBkg = r.TCanvas("canv_SigOverBkg","canv_SigOverBkg",600,600)
    canv_SigOverBkg.cd()
    grVFATSigOverBkg.SetTitle("")
    grVFATSigOverBkg.SetMarkerStyle(21)
    grVFATSigOverBkg.SetMarkerSize(0.7)
    grVFATSigOverBkg.SetLineWidth(2)    
    grVFATSigOverBkg.GetXaxis().SetTitle("VFAT Pos")
    grVFATSigOverBkg.GetYaxis().SetTitle("Sig / Bkg)")
    grVFATSigOverBkg.GetYaxis().SetTitleOffset(1.2)
    grVFATSigOverBkg.GetYaxis().SetRangeUser(0,20)
    grVFATSigOverBkg.GetXaxis().SetRangeUser(-0.5,24.5)
    grVFATSigOverBkg.Draw("APE1")
    canv_SigOverBkg.SaveAs(filename+'/SignalOverSigPBkg.png')

#Store - Signal
if options.performFit:
    canv_Signal = r.TCanvas("canv_Signal","canv_Signal",600,600)
    canv_Signal.cd()
    grVFATNSignalNoBkg.SetTitle("")
    grVFATNSignalNoBkg.SetMarkerStyle(21)
    grVFATNSignalNoBkg.SetMarkerSize(0.7)
    grVFATNSignalNoBkg.SetLineWidth(2)    
    grVFATNSignalNoBkg.GetXaxis().SetTitle("VFAT Pos")
    grVFATNSignalNoBkg.GetYaxis().SetTitle("Signal Hits")
    grVFATNSignalNoBkg.GetYaxis().SetTitleOffset(1.5)
    grVFATNSignalNoBkg.GetYaxis().SetRangeUser(0,nTrig)
    grVFATNSignalNoBkg.GetXaxis().SetRangeUser(-0.5,24.5)
    grVFATNSignalNoBkg.Draw("APE1")
    canv_Signal.SaveAs(filename+'/SignalNoBkg.png')

#Store - Max Hits By Lat Per VFAT
canv_MaxHitsPerLatByVFAT = r.TCanvas("canv_MaxHitsPerLatByVFAT","canv_MaxHitsPerLatByVFAT",1200,600)
canv_MaxHitsPerLatByVFAT.Divide(2,1)
canv_MaxHitsPerLatByVFAT.cd(1)
grNMaxLatBinByVFAT.SetTitle("")
grNMaxLatBinByVFAT.SetMarkerStyle(21)
grNMaxLatBinByVFAT.SetMarkerSize(0.7)
grNMaxLatBinByVFAT.SetLineWidth(2)    
grNMaxLatBinByVFAT.GetXaxis().SetRangeUser(-0.5,24.5)
grNMaxLatBinByVFAT.GetXaxis().SetTitle("VFAT Pos")
grNMaxLatBinByVFAT.GetYaxis().SetRangeUser(0,nTrig)
grNMaxLatBinByVFAT.GetYaxis().SetTitle("Hit Count of Max Lat Bin")
grNMaxLatBinByVFAT.GetYaxis().SetTitleOffset(1.7)
grNMaxLatBinByVFAT.Draw("APE1")
canv_MaxHitsPerLatByVFAT.cd(2)
grMaxLatBinByVFAT.SetTitle("")
grMaxLatBinByVFAT.SetMarkerStyle(21)
grMaxLatBinByVFAT.SetMarkerSize(0.7)
grMaxLatBinByVFAT.SetLineWidth(2)    
grMaxLatBinByVFAT.GetXaxis().SetTitle("VFAT Pos")
grMaxLatBinByVFAT.GetYaxis().SetTitle("Max Lat Bin")
grMaxLatBinByVFAT.GetYaxis().SetTitleOffset(1.2)
grMaxLatBinByVFAT.GetXaxis().SetRangeUser(-0.5,24.5)
grMaxLatBinByVFAT.Draw("APE1")
canv_MaxHitsPerLatByVFAT.SaveAs(filename+'/MaxHitsPerLatByVFAT.png')

#Store - TObjects
outF.cd()
grNMaxLatBinByVFAT.SetName("grNMaxLatBinByVFAT")
grNMaxLatBinByVFAT.Write()
grMaxLatBinByVFAT.SetName("grMaxLatBinByVFAT")
grMaxLatBinByVFAT.Write()
if options.performFit:
    grVFATSigOverBkg.SetName("grVFATSigOverBkg")
    grVFATSigOverBkg.Write()
    grVFATNSignalNoBkg.SetName("grVFATNSignalNoBkg")
    grVFATNSignalNoBkg.Write()
outF.Close()
