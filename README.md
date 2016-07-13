Chooseable-Path Adventure Tracker
=================================

ABOUT
-----

This is a utility to help keep track of where you've been inside a
Chooseable-Path Adventure novel such as the ones written by
Ryan North <sup>[1](#fn1)</sup> (*To Be or Not To Be* <sup>[2](#fn2)</sup>,
*Romeo and/or Juliet* <sup>[3](#fn3)</sup>).  It'd also be usable,
of course, for the original Choose-Your-Own-Adventure novels on
which the concept was based, though a few features included here
wouldn't have much use for those books.

My main purpose in writing this is that I'd always wanted to have
a better view into what paths I'd already taken in the book, and more
to the point, which paths I'd missed.  After you've reached a few
dozen endings, a lot of the beginning parts start to become a little
too familiar, and remembering where you've got unexplored paths can
be a bit cumbersome.  This utility is *basically* just a fancy
electronic bookmark for myself.

The utility can also output some fancy graphs, using a third party
application called Graphviz <sup>[4](#fn4)</sup>.  The graphs can
become rather unwieldy as the book is populated, but they're a great
way to have a visual "bookmark" of all the places you have yet to
explore in the book, and it's probably the most useful thing this
utility generates.  You can find some examples in the `examples`
directory.

This application is licensed under the New/Modified BSD License.
See COPYING.txt for details.

INSTALLATION
------------

**Requirements:**
* Python <sup>[5](#fn5)</sup> - The app should be usable with either
  python2 or python3, though my main desktop still uses python2 as
  a default, so it's been tested more thoroughly with that version.
* PyYAML <sup>[6](#fn6)</sup> - The app saves its data in the YAML <sup>[7](#fn7)</sup>
  format.
* Graphviz <sup>[4](#fn4)</sup> *(optional)* - If you want to
  generate some fancy graphs.  The graphs are sort of the most useful
  feature of the app, by far, so you almost certainly do want this.
* Colorama <sup>[8](#fn8)</sup> *(optional)* - For nicely-colorized
  text output in the CLI.

There isn't actually an installation procedure at the moment.  I
suppose I should probably turn it into a properly-packaged Python
thing, but for now I just run it directly from the directory it
lives in.

The utility needs to be run from a commandline of some sort.  I use
Linux, so living in a CLI is second nature to me.  Users on Windows
or OSX should theoretically be able to use this, though it's not
been tested on those platforms.  Just make sure to launch it from
a commandline (`cmd.exe` or Powershell on Windows, or Terminal on OSX).
Users on other Python-capable platforms are hopefully already aware
of what would need to happen there.

Included in the `examples` directory is a very-incomplete start to
*Romeo and/or Juliet*, with the filename `romeo.yaml`, so you can take a
look at that if you want.  Given that the intent here is sort of as a
personal "bookmarking" system, it doesn't make much sense to start
with an already-filled-out tree, but you can also check out a 
complete version of the book at `romeo_full.yaml` if you'd like to
mega-cheat.

USAGE
-----

You must specify a filename with the `-f` or `--filename` option:

    ./choosable.py -f romeo.yaml
    ./choosable.py --filename romeo.yaml

If the file doesn't exist, you'll be asked if you want to create a
new one.  I tend to use `.yaml` for the file extension, but the actual
extension doesn't matter.  Once you launch the app, you'll have a
commandline interface with which to edit the book, create new pages,
etc.

You can get some fancy colorization on the app if the python library
"Colorama" is installed.  You can specify either `light` or `dark`
with the `-c` or `--color` option, if you're using a terminal with a
light or dark background, respectively:

    ./choosable.py -f romeo.yaml -c dark
    ./choosable.py --filename romeo.yaml --color light

You can also change the color scheme while the app is running.

Upon launching the app, you'll be presented with a screen similar
to the following:

    Chooseable-Path Adventure Tracker

    Loaded Book "Romeo and/or Juliet"

    --------------------------------------------------------------------------------
    **** CANON ****
    Current Page: 1
    Current Character: Other

    Summary: Book Introduction

      Spoil the plot (turn to page 3 - visited (CANON))
      Learn more about the author (turn to page 22 - visited)
      Play without spoilers (turn to page 36 - visited (CANON))
    --------------------------------------------------------------------------------
    [a] Add Choice [d] Delete Choice [c] Character
    [p/##] Page [x] Delete Page [l] List Pages [u] Update Summary
    [t] Toggle Canonical [e] Toggle Ending
    [i] Add Intermediate [o] Delete Intermediate
    [s] Save [g] Graphviz [q] Quit [r] Swap Color Style
    Action: 

So up at the top you'll see that page 1 is considered "canon," and
we're currently using the character "Other."  There's a summary of
the current page, and then a list of choices.  If there's a Page entry
already for the destination page, it'll list "visited" after the
choice text, and if the destination choice is considered canonical,
it'll list that as well.

Most of the available options are pretty self-explanatory.  To add or
delete a choice, use `a` and `d`.  Note that there's currently no way
to modify a choice.  If you make a mistake, you'll have to just delete
the choice and then re-add it.

To change the current character on this page, use `c`, and you'll end
up at a dialog like the following:

    Current Characters:
      [1] Juliet
      [2] Other (*)
      [3] Romeo

      [n] New Character
      [d] Delete Character
      [e] Edit Character (name, graphviz colors)

    Switch to character number [2]: 

In addition to switching the currently-active character, you can also
add and delete characters from this menu, and also edit character names
and their graphviz colors.

Back on the main menu, if you use `p` or just type in a new page number,
you'll either switch to that page (if it already exists in the system), or
create a new page (if it doesn't).  If you create a new page, you'll be
prompted for the new page summary, and the character of the page will be
retained from the page you were just on.

Pages can be deleted with `x`, but note that the app will not allow you to
delete the page that you're currently on.

To list all pages, use `l`.  This will also print out various statistics
about the book that you're editing, like so:

    Total pages known: 30
    Canon Pages: 24
    Ending Pages: 2
    Intermediate Pages: 6
    Character Counts:
      Hamlet: 16 pages
      Ophelia: 6 pages
      Other: 7 pages
      Ryan North: 1 page

To update the summary of the current page, use `u`.  Pages have two toggle
switches: one for canon, and the other for "ending," intended to be used on
all the ending pages.  (Mostly that's just useful for colorization on the
graphs - more on that later.)  You can toggle either of those with `t` and
`e` respectively.

To add or edit "intermediate" pages, use `i` and `o`, though this is a
feature you probably don't care about.  See the section about Pages and
Intermediate Pages, below.

To generate a Graphviz dotfile and PNG, use `g` (more on that in the next
section).  This will generate two files, a text-based dotfile which Graphviz
understands, and a PNG graphic (so long as Graphviz is available in your path).

To change the color scheme currently in use, use `r` (this is only
available if the "colorama" Python library is installed).

Finally,  you can save to the current filename with `s`, or quit with `q`.
The app will ask you if you want to save before quitting.

GRAPHVIZ
--------

Graphviz is an awesome application which translates a
generally-human-readable text file (in the correct format, of course),
and turns it into nifty graphs automatically for you.  One of its
modes, "dot," is the flowchart-like directional graph which is most
useful for visualizing this kind of data, and the utility supports
exporting to a "dot" file for graphviz to parse.

When you generate a dotfile in the app with the `g` option, it will
also try to call `dot` to generate the PNG automatically.  This
attempt will fail if you don't have `dot` in your `$PATH`, but you
will still have a dotfile saved so that you can run it manually
later.

You can also generate a dotfile outside of the main app UI, with
the `-d` or `--dot` option, like so:

    ./choosable.py -f romeo.yaml -d romeo.dot
    ./choosable.py --filename romeo.yaml --dot romeo.dot

If `romeo.dot` already exists, you'll be prompted as to whether you
want to overwrite it.  Then once you have the dotfile, you can use
graphviz's "dot" utility to create a PNG image like so:

    dot -Tpng romeo.dot -o romeo.png

Alternatively, I've included a `makedot.sh` script which will
auto-convert any `*.dot` file in the current directory to a PNG.
That's a shell script <sup>[9](#fn9)</sup>, which is only going
to work on systems which support shell scripts.  (Linux, of
course, works.  OSX probably will?)  The script has only been
tested with "bash" <sup>[10](#fn10)</sup>, though I'd be surprised
if alternate shells like dash wouldn't work.

Graphviz can output to many other formats than just PNG, though
I haven't actually tested out the current dotfile generation with
anything but PNGs.  The generated graphs can get pretty unwieldy,
but I've found them to be quite useful even when they get huge.

Each of the characters has a set of colors associated with it, which
will be put into the graphviz graphs that are generated.  The
default colors are black text with a white background.  To change
the colors, you can use the `c` option from the main UI, and then
hit `e` to edit a character.  The list of colors that Graphviz 
accepts is found here: http://www.graphviz.org/doc/info/colors.html

"PAGES" AND INTERMEDIATE PAGES
------------------------------

This section is really only useful for someone who's hoping to use this
utility to ensure that they've seen 100% of the book in question.  In
*Romeo and/or Juliet*, what we call a "page" isn't really a physical page.
In fact, the book itself eschews that term, and instead of "Turn to page
282," it just says "Turn to 282."  Each number can span multiple physical
pages, depending on the length of the text, and each physical page can
contain multiple numbers.

This makes it pretty easy for the app to discover if there are any "holes"
in the list of discovered pages.  In fact, the `l` option to list pages
will include a list of missing "pages" so long as there are fewer than
20 (otherwise the list could be super long).  For instance, on my
`romeo_full.yaml` file, you'd see the following:

    Missing pages (13 total):
    [243, 253, 261, 269, 276, 285, 295, 305, 317, 321, 331, 340, 342]

(Which is expected because I didn't actually catalogue the entire Caesar
Cipher puzzle, since the graph quickly becomes ludicrously unwieldy.)

Anyway, for a book set up like *Romeo and/or Juliet*, where every "page
number" corresponds to a choice, and there's no holes, that Missing-Page
logic works great as-is.

In traditional Choose-Your-Own Adventure novels, and also in *To Be or
Not To Be*, however, the instructions do refer to actual page numbers,
and the options may span multiple pages.  Every ending scene in *To Be
or Not To Be*, in particular, will have at least one intermediate page
to hold the full-page illustration.

Without a way to catalogue these intermediate pages, it'd be impossible
for the app to determine if there are any "holes" in the catalogued
pages.  So, that's what the app means by intermediate pages.  You can
add or delete them with `i` or `o`.  When you go into the delete mode,
you'll see all the current pages marked, like so:

    Current intermediates:
       2, 5, 47, 358, 480, 481

    Intermediate to delete (enter to quit): 

For both adding and deleting, you can just keep typing in numbers
if you want to do a bunch all at once, and hit Enter to exit out of
the intermediate number management mode.

Again, this is clearly only something that you'd want to bother with
if you're: 1) Reading a book like *To Be or Not To Be*, where choices can
span multiple physical pages, and 2) Trying to make sure that you get
100% completion on the book.  If that *is* something you think you're
interested in, it's probably best to start cataloguing them right from
the start of your reading, so it's not a lot of work to add in later.

NON-NUMERIC PAGE NUMBERS
------------------------

The book *To Be Or Not To Be* features a book-within-a-book called
*The Murder of Gonzago* which uses a completely separate page numbering
scheme from the rest of the book.  It's a full 24 pages (including
"cover") right inbetween the real pages 414 and 415.  The pages are
numbered with a special system where page 1 is "G001" and page 21 is
"G021", etc.

This posed some problems for prior versions of this utility, since we
assumed that all page numbers are numeric, and there was no good way
to keep track of the nested book.  There are a few possible ways to solve
this, but in the end it was simplest to just allow page numbers to be
non-numeric.

In general, the functionality for dealing with non-numeric page numbers
like the sorts found in *The Murder of Gonzago* doesn't change at all.
The one difference is that in order to move to a page like G020, or to
switch to that page, you **must** use the `p` option directly rather
than just typing the page number in at the main command prompt.  That's
a little less convenient than it could potentially be, but given that
this is a very special case unlikely to be found in any other book,
I don't think it poses much trouble really.

Note that the "missing page" detection outlined above completely
ignores non-numeric pages, so you'll have to just make sure that
you've seen the whole *Murder of Gonzago* by hand, so to speak.

DEVIATIONS
----------

There's a few ways in which the data collected by this app differs
from the "data" contained in the actual Choosable-Path Adventure
books by Ryan North.

* In the books, it's the CHOICES which are considered canonical,
  not the pages themselves.  The app assigns canon to the page,
  though, so there's a few places where you can have two separate
  "canonical" choices on the same page while using the app.
  Generally when you have the option to skip over dialogue or
  the like.
* The books occasionally have two separate choices which lead to
  the same page, for humorous purposes.  We only support a single
  choice per target page, so those are collapsed a bit.
* The book orders the player choices in a way designed to maximize
  humor.  The internal data structure we use does not preserve
  choice order at all, and will always just sort them in page order.

TODO
----

* The app doesn't really follow a super-strict separation of data
  objects and application logic.  The main App class probably knows
  too much about the internal structure of the Book/Option/Character
  classes, for instance.
* Strict adherents to PEP8 <sup>[11](#fn11)</sup> will probably weep
  in sorrow after looking at this code.  I apologize.
* There's no way to *modify* existing choices.  To make a change to
  a choice, you've got to delete it and then re-add.
* There's also no way to modify the book title itself, though that
  could be easily edited by hand in the YAML file directly.
* I seem to be inconsistent with "choosable" versus "chooseable."  The
  printed book uses the E, though it seems that the more-canonical
  spelling is without?  Given that the books themselves do not especially
  respect canon, I don't think that's a particularly strong argument,
  though.

FOOTNOTES!
----------

<a name="fn1">1</a>: http://www.qwantz.com/
<a name="fn2">2</a>: http://qwantz.com/tobeornottobe.php
<a name="fn3">3</a>: http://www.romeoandorjuliet.com/
<a name="fn4">4</a>: http://www.graphviz.org/
<a name="fn5">5</a>: https://www.python.org/
<a name="fn6">6</a>: http://pyyaml.org/wiki/PyYAML
<a name="fn7">7</a>: http://yaml.org/
<a name="fn8">8</a>: https://pypi.python.org/pypi/colorama
<a name="fn8">9</a>: https://en.wikipedia.org/wiki/Shell_script
<a name="fn9">10</a>: https://www.gnu.org/software/bash/
<a name="fn10">11</a>: https://www.python.org/dev/peps/pep-0008/

