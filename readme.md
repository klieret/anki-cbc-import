# Anki-Addon: cbc-Import

This addon adds a new toolbar to Anki's "Add Card" dialog, that lets the user load csv files, containing new vocabularywhich can then added step by step. This way, the Expression, Meaning and Reading fields will be filled automatically, but the user can add more information to the cards before adding them. For me, this is more effective than other workflows (such as first importing all cards from csv, then accessing them from the browser again to modify & extend them).

I'm using this Addon since quite some time, but haven't really done too much testing, so it's likely to not work out of the box right away for anyone. Still, I think it's a pretty cool thing and if more people are interested, I'd invest more time to make it work for anyone (of even, better if someone would help me with getting it readyof course).

![screenshot](https://github.com/klieret/readme-files/blob/master/anki-cbc-import/Selection_004.png)

## Installation

Click here HERE to download the newest version of this addon as a ZIP file, then move the contents of the ZIP folder (the file ```cbcImport.py``` and the folder ```cbcImport```) to the ```addon``` subfolder of your Anki directory. 

E.g. Linux: ```~/Documents/Anki/addons```, Windows ```<path to your account>/Documents/Anki/addons```.

## Usage

Buttons (hover over them to see the corresponding keystrokes):
* ```File```: Click this button to browse for a new ```.csv``` file to open
* ```Load```: After selectinv a ```.csv``` file with the ```File``` button, click this button to load the entries
* ```Show```: Opens the ```.csv``` file in a text-editor (you might have to modify the source to select the editor of your choice/your platform)
* ```Reverse```: Reverse the order of the vocabulary items in the queue.
* ```Save```: Save ```.csv``` files containing already added, blacklisted, remaining vocabulary items etc.
* ```<<```: Go to beginning of queue
* ```<```: Go to previous queue item
* ```X```: Copy data of the current queue item to the entry fields
* ```>```: Go to next queue item
* ```>>```: Go to last queue item
* ```Hide```/```Advanced```: Show row of check-boxes and information below this row of buttons

Labels:
* ```In```: Currently selected ```.csv``` file
* ```Cur```: Index of the current item in the queue/Total number of items in the queue (ignoring blacklisted, already added items)
* ```Idx```: Index of the current item/Total number of items (including all blacklisted and already added items)
* ```Add```: Number of added notes
* ```Dup```: Number of duplicate notes
* ```Black```: Number of blacklisted notes."
* ```LA```: ("last added") Was the last note added to the Anki collection (and not skipped)?
 
Checkboxes:

* ```Skip Dupe```: Skip duplicate entries (entries that would be flagged by Anki's duplicate finder; note that this requires my addon [ignore dupes](https://github.com/klieret/anki-ignore-dupes)
* ```Skip Added```: Skip already added entries
* ```Skip Black```: Skip blacklisted entries
* ```Skip Rest```: Skip all other entries
* ```Auto Insert```: Automatically insert the fields from the queue item in the entry fields above, when we hit buttons such as ```>```, ```<``` etc. (else you need to press ```X``` to fill in the information every time)
* ```Blacklist Current```: Blacklist current card

## License

The contents of this repository are licensed under the [*AGPL3* license](https://choosealicense.com/licenses/agpl-3.0/) (to be compatible with the license of Anki and its addons as detailed [here](https://ankiweb.net/account/terms)).
