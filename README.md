# PyCorderPlus

`PyCorderPlus` is an updated version of `PyCorder`, which has been rewritten to a new version of `Python3` and added support for working with `NeoRec` EEG amplifiers.

*PyCorder is a graphical application for working with EEG data and impedance obtained from Actichamp Plus amplifiers from BrainVision*
## Overview

`PyCorderPlus` allows you to work with EEG amplifiers (`actiCHamp` and `NeoRec`) and supports the following functionality:
1. Displaying EEG and impedance signals from an amplifier
2. Saving the signals received from the amplifier in the format `.eeg`
3. Setting up the amplifiers
4. Signal filtering

In `PyCorderPlus`, the main modules of the `PyCorder` program were rewritten to a new version of the `Python` language. 
The work was not fully completed, due to the difficulties that arose due to the fact that some libraries were no longer supported (for example, `Qwt` in `PyQt`).
The work done can be found in the `Release History`.

In the future, it is planned to eliminate errors and reproduce the full functionality of the `PyCorder` program.
The errors found can be found in the `List of found errors`.

## Installation

To use `PyCorderPlus` you need to install `Python` and libraries. Libraries can be installed in two ways.

 1. By running the `install.bat`

 2. Using commands in the terminal while in the program directory

```commandline
python -m venv venv
./venv/Scripts/activate
pip install -r requirements.txt
```

## Running

You can start the program by activating the `run.bat` or by typing in the terminal in the program directory.

```commandline
./venv/Scripts/activate
python -m main.py
```

If you are opening `PyCorderPlus` for the first time, then you need to install the libraries.



## Dependencies

### Amplifier Drivers

* Driver for [actiCHamp Plus](actiCHampDriver)
* To work with NeoRec amplifiers, you do not need to install drivers, the amplifiers work via Bluetooth


### Requirements
* Python >= 3.11

### System requirements
* OS: Windows 10

### Requirements for libraries
You can find other requirements for the library in the [requirements.txt](requirements.txt).

## Copyrights
### Main code base
Copyright © 2010, Brain Products GmbH, Gilching, for original PyCorder modules

Copyright © 2024, Medical Computer Systems Ltd, for modules rewritten to a new version of Python

### PyCorderPlus NeoRec Recorder
Copyright ©  2024, Medical Computer Systems Ltd, for modules for receiving and processing data from NeoRec amplifiers

## License
See included [LICENSE](LICENSE) file for more details about licensing terms.

## Release History
### v1.0.0
* Modules completely rewritten: `modbase.py`, `storage.py`, `impedance.py`, `filter.py`, `tools.py`, `trigger.py`
* Modules partially rewritten: `amplifier_actichamp.py`, `actichamp_w.py`, `display.py`, 
* Added support for NeoRec amplifiers.

## List of found errors
1. When connecting a NeoRec cap, it is possible to double the number of channels in the display.

![Error example](res/error_img.JPG)