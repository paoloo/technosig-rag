"""Transparent technosignature/RF vocabulary tags used as retrieval metadata."""
from __future__ import annotations
import re

def _p(*terms: str): return re.compile(r"\b(?:" + "|".join(terms) + r")\b", re.I)

PATTERNS = {
 "facilities": {
  "ATA": _p(r"Allen Telescope Array", r"ATA"), "FAST": _p(r"FAST", r"Five-hundred-meter Aperture Spherical Telescope"),
  "GBT": _p(r"Green Bank Telescope", r"GBT"), "MeerKAT": _p(r"MeerKAT"), "VLA": _p(r"Very Large Array", r"VLA"),
  "Parkes/Murriyang": _p(r"Parkes", r"Murriyang"), "LOFAR": _p(r"LOFAR"), "MWA": _p(r"Murchison Widefield Array", r"MWA"),
  "Arecibo": _p(r"Arecibo"), "Lick/APF": _p(r"Automated Planet Finder", r"APF", r"Lick Observatory"),
 },
 "technosignatures": {
  "narrowband radio": _p(r"narrow[ -]?band", r"continuous wave"), "broadband pulses": _p(r"broadband pulse", r"impulsive signal"),
  "optical laser": _p(r"optical SETI", r"laser pulse", r"laser emission"), "waste heat": _p(r"waste heat", r"Dyson sphere"),
  "atmospheric pollution": _p(r"atmospheric pollution", r"industrial pollutant"), "transit artifacts": _p(r"artificial transit", r"megastructure"),
  "radio leakage": _p(r"radio leakage", r"unintentional emission"), "artificial satellites": _p(r"artificial satellite", r"Clarke belt"),
 },
 "signal_features": {
  "Doppler drift": _p(r"Doppler drift", r"drift rate"), "SNR": _p(r"signal[ -]?to[ -]?noise", r"SNR"),
  "dispersion": _p(r"dispersion measure", r"dispersed pulse"), "polarization": _p(r"polari[sz]ation"),
  "modulation": _p(r"modulat(?:ion|ed)"), "bandwidth": _p(r"bandwidth"), "cadence": _p(r"cadence", r"on[ -]?off observation"),
 },
 "methods": {
  "turboSETI": _p(r"turboSETI"), "setigen": _p(r"setigen"), "BLIMPY": _p(r"BLIMPY"), "deep learning": _p(r"deep learning", r"neural network"),
  "machine learning": _p(r"machine learning"), "coincidence rejection": _p(r"coincidence rejection", r"multi[ -]?beam coincidence"),
  "RFI mitigation": _p(r"RFI mitigation", r"radio frequency interference", r"interference rejection"),
 },
 "data_products": {
  "filterbank": _p(r"filterbank", r"SIGPROC"), "voltage data": _p(r"baseband", r"voltage data", r"raw voltage"),
  "dynamic spectrum": _p(r"dynamic spectr", r"waterfall"), "candidate events": _p(r"candidate event", r"hit table"),
  "visibility data": _p(r"visibility data", r"visibilities"), "image cube": _p(r"image cube", r"spectral cube"),
 },
}

def extract_tags(text: str) -> dict[str, list[str]]:
    return {group: [name for name, pattern in values.items() if pattern.search(text)] for group, values in PATTERNS.items()}
