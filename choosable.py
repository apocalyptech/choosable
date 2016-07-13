#!/usr/bin/env python
# vim: set expandtab tabstop=4 shiftwidth=4:
#
# Copyright (c) 2016, CJ Kucera
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the development team nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL CJ KUCERA BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import os
import sys
import yaml
import argparse
import itertools
import subprocess

try:
    import colorama
except ImportError:
    pass

class Character(object):
    """
    Class to hold information about a character.  Note that
    there is currently no UI to change colors - they must
    be edited directly in the YAML.
    """

    def __init__(self, name):

        self.name = name
        self.fillcolor = 'white'
        self.fontcolor = 'black'

    def to_dict(self):
        """
        Returns a dictionary representation of ourself, for use
        in YAML saving.
        """
        savedict = {}
        savedict['name'] = self.name
        savedict['graphviz_fillcolor'] = self.fillcolor
        savedict['graphviz_fontcolor'] = self.fontcolor
        return savedict

    @staticmethod
    def from_dict(chardict):
        """
        Converts a dictionary (from YAML save) to an object
        """
        char = Character(chardict['name'])
        char.fillcolor = chardict['graphviz_fillcolor']
        char.fontcolor = chardict['graphviz_fontcolor']
        return char

class Choice(object):
    """
    A choice the reader can take.  Note that we're not actually
    linking directly to remote Page objects here because those
    objects won't exist until we create them, but we still want
    to keep track of what choices exist on any given page.
    Perhaps that's lame.  Ah well.
    """

    def __init__(self, target, summary):

        self.target = target
        self.summary = summary

    def to_dict(self):
        """
        Returns a dictionary representation of ourselves, for use
        in saving to YAML.
        """
        savedict = {}
        savedict['target'] = self.target
        savedict['summary'] = self.summary
        return savedict

    @staticmethod
    def from_dict(choicedict):
        """
        Converts a dictionary (from YAML save) to object and returns.
        """
        choice = Choice(choicedict['target'], choicedict['summary'])
        return choice

    def print_text(self):
        """
        Prints out a text representation of ourself.
        """
        print('  %s -> %s' % (self.summary, self.target))

class Page(object):
    """
    A page!  (Well, okay, Romeo and/or Juliet doesn't technically
    restrict these to one per physical page, but whatever.)
    """

    def __init__(self, pagenum, character=None, summary=None, canonical=False, ending=False):

        self.pagenum = pagenum
        self.character = character
        self.summary = summary
        self.canonical = canonical
        self.ending = ending

        self.choices = {}

    def to_dict(self):
        """
        Returns a dictionary representation of ourselves, for use in
        saving to YAML format.
        """
        savedict = {}
        savedict['pagenum'] = self.pagenum
        savedict['character'] = self.character.name
        savedict['summary'] = self.summary
        savedict['canonical'] = self.canonical
        savedict['ending'] = self.ending
        savedict['choices'] = {}
        for choice in self.choices.values():
            savedict['choices'][choice.target] = choice.to_dict()
        return savedict

    @staticmethod
    def from_dict(pagedict, characters):
        """
        Converts a dictionary (from YAML save) to Page object.
        Needs a characters structure so that we can assign page
        ownership properly.
        """
        if pagedict['character'] not in characters:
            raise Exception('Character "%s" not found for page %s' % (pagedict['character'], pagedict['pagenum']))
        page = Page(pagedict['pagenum'],
                character=characters[pagedict['character']],
                summary=pagedict['summary'],
                canonical=pagedict['canonical'],
                ending=pagedict['ending'])
        for choicedict in pagedict['choices'].values():
            page.add_choice_obj(Choice.from_dict(choicedict))
        return page

    def print_text(self):
        """
        Prints out a text summary of ourselves
        """
        print('Page %s (%s) - %s' % (self.pagenum, self.character.name, self.summary))
        for choice in self.choices_sorted():
            choice.print_text()
        print('')

    def add_choice(self, target, summary):
        """
        Adds a new choice, with the target pagenumber.  Returns
        the choice object
        """
        choice = Choice(target, summary)
        return self.add_choice_obj(choice)

    def add_choice_obj(self, choice):
        """
        Adds a choice object to our list of choices and returns it.
        """

        # There are technically a few pages which have multiple choices
        # which go to the same page, but we'll just consider those
        # collapsed.
        if choice.target in self.choices:
            raise Exception('Target %s already exists on page %s' % (choice.target, self.pagenum))

        self.choices[choice.target] = choice
        return choice

    def choices_sorted(self):
        """
        Returns a list of choices sorted by page number
        """
        return [self.choices[idx] for idx in sorted(self.choices.keys())]

    def delete_choice(self, target):
        """
        Deletes the choice pointing at the specified target.  Raises
        an KeyError if the target is not found
        """
        del self.choices[target]

    def toggle_canonical(self):
        """
        Toggles our canonical state
        """
        self.canonical = not self.canonical

    def toggle_ending(self):
        """
        Toggles our 'ending' stage
        """
        self.ending = not self.ending

class Book(object):
    """
    The main Book object.  Mostly just contains dicts for characters
    and pages, but also keeps track of the running filename so we don't
    have to remember it otherwise.
    """

    def __init__(self, title, filename=None):

        self.title = title
        self.filename = filename
        self.characters = {}
        self.pages = {}
        self.intermediates = {}

    @staticmethod
    def load_from_dict(savedict):
        """
        Given a dictionary (from a YAML file), load ourselves.
        """

        book = Book(savedict['book']['title'])

        # "intermediates" is a new variable, don't rely on it being
        # in the file.
        if 'intermediates' in savedict:
            for intermediate in savedict['intermediates']:
                book.add_intermediate(intermediate)

        for chardict in savedict['characters'].values():
            book.add_character_obj(Character.from_dict(chardict))
        for pagedict in savedict['pages'].values():
            book.add_page_obj(Page.from_dict(pagedict, book.characters))

        return book

    @staticmethod
    def load(filename):
        """
        Loads from a YAML filename, returns a new Book object.
        """
        data = None
        with open(filename, 'r') as df:
            data = yaml.load(df.read())

        if data is None:
            raise Exception('YAML data not found in file')

        # Now do the object population
        book = Book.load_from_dict(data)
        book.filename = filename
        return book

    def get_savedict(self):
        """
        Get a dictionary of ourselves, suitable for passing in to a YAML
        save function.
        """

        if len(self.characters) == 0:
            raise Exception('Refusing to save game with no characters defined')

        if len(self.pages) == 0:
            raise Exception('Refusing to save game with no pages defined')

        savedict = {}
        savedict['book'] = {
                'title': self.title,
            }

        savedict['characters'] = {}
        for character in self.characters.values():
            savedict['characters'][character.name] = character.to_dict()

        savedict['pages'] = {}
        for page in self.pages.values():
            savedict['pages'][page.pagenum] = page.to_dict()

        savedict['intermediates'] = []
        for intermediate in self.intermediates_sorted():
            savedict['intermediates'].append(intermediate)

        return savedict

    def save(self, filename=None):
        """
        Saves out the book, in YAML format.  Pass in a filename to
        use something other than the default.
        """

        if filename is None and self.filename is None:
            raise Exception('No filename has been specified to save!')

        if filename is None:
            filename = self.filename

        # Get the dictionary
        savedict = self.get_savedict()

        # Save ourselves out
        with open(filename, 'w') as df:
            yaml.dump(savedict, df)

        # And that's it!

    def print_text(self):
        """
        Prints out a text summary of the book
        """
        print('')
        print('Title: %s' % (self.title))
        print('')
        for page in self.pages.values():
            page.print_text()

    def add_character(self, name):
        """
        Adds a new character to the book and returns the char object.
        """

        char = Character(name)
        return self.add_character_obj(char)

    def add_character_obj(self, char):
        """
        Adds a character object to the book, and returns it.
        """
        if char.name in self.characters:
            raise Exception('Character "%s" is already present in book' % (char.name))
        self.characters[char.name] = char
        return char

    def rename_character(self, char, newname):
        """
        Renames the given character object to a new name.  Will raise an
        Exception if things aren't kosher
        """

        # We've probably already checked for this at input time, but
        # regardless: check to make sure there's not already a
        # character with the new name.
        if newname in self.characters and self.characters[newname] != char:
            raise Exception('Cannot rename character "%s" to "%s" because a character already exists with that name' % (
                char.name, newname))

        del self.characters[char.name]
        char.name = newname
        self.add_character_obj(char)

    def delete_character(self, charname):
        """
        Deletes the given character name.  Will raise an Exception if
        things aren't kosher
        """

        # First sanity check
        if charname not in self.characters:
            raise Exception('Character "%s" not found to delete!' % (charname))

        # Next check for page ownership (this is almost certainly already
        # checked-for before this, but do it here as well)
        for page in self.pages_sorted():
            if page.character.name == charname:
                raise Exception('Character "%s" is the active character on page %s!' % (charname, page.pagenum))

        # Now go ahead and delete it
        del self.characters[charname]

    def add_page(self, pagenum, character=None, summary=None):
        """
        Adds a page to the book, and returns the page object.
        """

        page = Page(pagenum, character=character, summary=summary)
        return self.add_page_obj(page)

    def add_intermediate(self, pagenum):
        """
        Adds an intermediate page to the book.  Does not complain
        if the pagenum is already an intermediate
        """
        self.intermediates[pagenum] = True

    def delete_intermediate(self, pagenum):
        """
        Deletes an intermediate page from the book.  Does not complain
        if the pagenum is not already an intermediate
        """
        if pagenum in self.intermediates:
            del self.intermediates[pagenum]

    def has_intermediate(self, pagenum):
        """
        Returns True if the specified pagenum is an intermediate, and
        false otherwise
        """
        return (pagenum in self.intermediates)

    def print_intermediates(self, prefix='', num_per_line=10):
        """
        Prints out a list of our intermediates to the screen, with
        the given prefix and the given number of pages per line.
        Method taken from: http://stackoverflow.com/questions/434287/what-is-the-most-pythonic-way-to-iterate-over-a-list-in-chunks
        """
        args = [iter(self.intermediates_sorted())] * num_per_line
        for pagenums in itertools.izip_longest(*args):
            numlist = [str(x) for x in pagenums]
            while numlist[-1] == 'None':
                numlist.pop()
            print('%s%s' % (prefix, ', '.join(numlist)))

    def add_page_obj(self, page):
        """
        Adds a page object to the book, and returns it.
        """

        if page.pagenum in self.pages:
            raise Exception('Page %s already exists' % (page.pagenum))
        self.pages[page.pagenum] = page
        return page

    def delete_page(self, pagenum):
        """
        Deletes the specified page.  Will raise a KeyError
        if the page is not found
        """
        del self.pages[pagenum]

    def pages_sorted(self):
        """
        Returns a list of pages sorted by page number
        """
        return [self.pages[idx] for idx in sorted(self.pages.keys())]

    def intermediates_sorted(self):
        """
        Returns a list of intermediate pages sorted by page number
        """
        return sorted(self.intermediates.keys())

    def characters_sorted(self):
        """
        Returns a list of characters sorted by name
        """
        return [self.characters[name] for name in sorted(self.characters.keys())]

    def get_page(self, pagenum):
        """
        Gets a page, given a page number.  Will raise a KeyError
        if not found.
        """
        return self.pages[pagenum]

class App(object):
    """
    Main mostly-interactive application.  This class probably knows too much
    about the Book (and other) classes, and should probably abstract access to
    that stuff a bit more, but whatever.
    """

    COLOR_CHOICES = ['none', 'light', 'dark']
    COLOR_NONE = COLOR_CHOICES[0]
    COLOR_LIGHT = COLOR_CHOICES[1]
    COLOR_DARK = COLOR_CHOICES[2]

    def __init__(self):

        self.book = None
        self.cur_char = None
        self.cur_page = None

        # Check to see if we have the colorama module loaded.  There's...
        # probably a better way to do this?
        self.has_colorama = False
        try:
            if colorama:
                self.has_colorama = True
                colorama.init(autoreset=True)
        except NameError:
            pass

        # Parse arguments
        parser = argparse.ArgumentParser(description='Chooseable-Path Adventure Tracker',
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        parser.add_argument('-f', '--filename',
            required=True,
            type=str,
            help='Filename to load or create')
        parser.add_argument('-d', '--dot',
            type=str,
            metavar='DOTFILE',
            help='Output a graphviz DOT file instead of interactively editing')
        if self.has_colorama:
            color_help = 'Output colorization'
        else:
            color_help = 'Output colorization (REQUIRES COLORAMA)'
        parser.add_argument('-c', '--color',
            type=str,
            choices=App.COLOR_CHOICES,
            default='dark',
            help=color_help)
        args = parser.parse_args()

        # Store the data we care about
        self.filename = args.filename
        self.do_dot = args.dot
        if self.has_colorama:
            self.color = None
            self.set_color(args.color)
        else:
            self.color = App.COLOR_NONE
            print('Output colorization disabled - "colorama" Python package')
            print('required for colors.  See https://pypi.python.org/pypi/colorama')
            print('')

    def set_color(self, color=None):
        """
        Sets our color palette, or switches to the next one if color is not
        passed in.
        """

        # Just return if we don't have colorama installed
        if not self.has_colorama:
            return

        # Default to NONE, I guess.
        if color is None and self.color is None:
            self.color = App.COLOR_NONE
            return

        # If we didn't get passed in, assume we're just
        # switching styles.  Otherwise, set the color.
        if color is None:
            if self.color == App.COLOR_NONE:
                self.color = App.COLOR_LIGHT
            elif self.color == App.COLOR_LIGHT:
                self.color = App.COLOR_DARK
            else:
                self.color = App.COLOR_NONE
        else:
            if color in App.COLOR_CHOICES:
                self.color = color
        
        print('')
        self.print_result('Set color scheme to "%s"' % (self.color))
        print('')

    def color_dim(self):
        """
        Returns the dimming code, if we're supposed to
        """
        if self.has_colorama:
            if self.color == App.COLOR_LIGHT:
                return colorama.Style.DIM
            elif self.color == App.COLOR_DARK:
                return colorama.Style.BRIGHT
        return ''

    def color_bold(self):
        """
        Returns a bold escape sequence
        """
        if self.has_colorama:
            return colorama.Style.BRIGHT
        else:
            return ''

    def color_reset(self):
        """
        Returns an appropriate reset color
        """
        if self.has_colorama:
            return colorama.Style.RESET_ALL
        else:
            return ''

    def color_text(self, color):
        """
        Colorizes some text with the specified color
        """
        if self.has_colorama and self.color != App.COLOR_NONE:
            return '%s%s' % (self.color_dim(), color)
        else:
            return ''

    def color_intermediates(self):
        """
        Returns a color for use on listing intermediate pages
        """
        if self.has_colorama:
            if self.color == App.COLOR_LIGHT:
                return self.color_text(colorama.Fore.WHITE)
            elif self.color == App.COLOR_DARK:
                return self.color_text(colorama.Fore.BLACK)
        return ''

    def color_commands(self):
        """
        Color to use for command listings
        """
        if self.has_colorama:
            return self.color_text(colorama.Fore.CYAN)
        else:
            return ''

    def color_result(self):
        """
        Returns a color to use for results
        """
        if self.has_colorama:
            return self.color_text(colorama.Fore.GREEN)
        else:
            return ''

    def color_error(self):
        """
        Returns a color to use for errors
        """
        if self.has_colorama:
            return self.color_text(colorama.Fore.RED)
        else:
            return ''

    def color_heading(self):
        """
        Returns a color to use for headings
        """
        if self.has_colorama:
            return self.color_text(colorama.Fore.BLUE)
        else:
            return ''

    def color_prompt(self):
        """
        Returns a color to use for user prompts
        """
        if self.has_colorama:
            return self.color_text(colorama.Fore.YELLOW)
        else:
            return ''

    def color_flags(self):
        """
        Returns a color to use for page flags (ending, canon)
        """
        if self.has_colorama:
            return self.color_text(colorama.Fore.MAGENTA)
        else:
            return ''

    def print_heading(self, line):
        """
        Prints out a heading line
        """
        print('%s%s' % (self.color_heading(), line))

    def print_result(self, line):
        """
        Prints out an information line
        """
        print('%s%s' % (self.color_result(), line))

    def print_commands(self, line):
        """
        Prints out a command-info line
        """
        print('%s%s' % (self.color_commands(), line))

    def print_error(self, line):
        """
        Prints out an error line
        """
        print('%s%s' % (self.color_error(), line))

    def print_flags(self, line):
        """
        Prints out a flags line (canon, ending)
        """
        print('%s%s' % (self.color_flags(), line))

    def print_intermediates_line(self, line):
        """
        Prints out a line containing intermediate pages
        """
        print('%s%s' % (self.color_intermediates(), line))

    def prompt(self, prompt_text):
        """
        Prompts a user for input.  A simple wrapper.
        """
        sys.stdout.write('%s%s%s:%s ' % (self.color_prompt(), self.color_bold(), prompt_text, self.color_reset()))
        sys.stdout.flush()
        return sys.stdin.readline().strip()

    def prompt_yn(self, prompt_text, default=True):
        """
        Prompts for a user for input and assumes that it's a
        yes/no question.  Returns True or False, rather than
        the actual text.  The default response defaults to
        Yes but pass in default to change.
        """
        if default == True:
            optstr = 'Y|n'
        else:
            optstr = 'y|N'
        sys.stdout.write('%s%s%s [%s]? %s' % (self.color_prompt(), self.color_bold(), prompt_text, optstr, self.color_reset()))
        sys.stdout.flush()
        user_input = sys.stdin.readline().strip()
        if user_input == '':
            return default
        else:
            user_input = user_input[:1].lower()
            return (user_input == 'y')

    def edit_character(self):
        """
        Presents the user with a way to change a character's name
        or graphviz colors.
        """

        # Make sure we have some
        if len(self.book.characters) == 0:
            print('')
            self.print_error('No characters found to edit!')
            return

        # List of current characters
        print('')
        self.print_result('Current Characters:')
        clist = self.book.characters_sorted()
        for (idx, char) in enumerate(clist):
            print('  [%d] %s - Textcolor: %s, Fillcolor: %s' % (
                idx+1, char.name, char.fontcolor, char.fillcolor))
        print('')
        charnum_txt = self.prompt('Edit character (Enter to cancel)')
        if charnum_txt == '':
            return

        # Check for valid int
        try:
            charnum = int(charnum_txt)
        except ValueError:
            self.print_error('Please input a valid number!')
            print('')
            return self.edit_character()

        # Check for valid number
        if charnum < 1 or charnum > len(clist):
            self.print_error('Please input a number from 1 to %d' % (len(clist)))
            print('')
            return self.edit_character()

        # Grab which character we're talking about
        char = clist[charnum-1]

        # Get our input (name first)
        name = self.prompt('Character Name [%s]' % (char.name))
        if name == '':
            name = char.name

        # Make sure the new name doesn't already exist
        for c in clist:
            if c != char and name == c.name:
                print('')
                self.print_error('Another character is already named "%s"' % (name))
                return

        # Now get our colors
        fontcolor = self.prompt('Text Color (graphviz) [%s]' % (char.fontcolor))
        if fontcolor == '':
            fontcolor = char.fontcolor
        fillcolor = self.prompt('Fill Color (graphviz) [%s]' % (char.fillcolor))
        if fillcolor == '':
            fillcolor = char.fillcolor

        # Now make changes.  First, the easy stuff!
        char.fontcolor = fontcolor
        char.fillcolor = fillcolor
        self.print_result('Colors set!')

        # Now the slightly-more complex stuff
        if name != char.name:
            try:
                self.book.rename_character(char, name)
                self.print_result('Character name changed to "%s"' % (name))
            except Exception as e:
                self.print_error('Could not rename character: %s' % (e))

        return

    def delete_character(self):
        """
        Provides the user with options to delete a character.  Will
        refuse to delete a character who's active on any pages, though.
        """

        # Make sure we have some
        if len(self.book.characters) == 0:
            print('')
            self.print_error('No characters found to delete!')
            return

        # List of current characters
        print('')
        self.print_result('Current Characters:')
        clist = self.book.characters_sorted()
        for (idx, char) in enumerate(clist):
            print('  [%d] %s' % (idx+1, char.name))
        print('')
        charnum_txt = self.prompt('Delete character (Enter to cancel)')
        if charnum_txt == '':
            return

        # Check for valid int
        try:
            charnum = int(charnum_txt)
        except ValueError:
            self.print_error('Please input a valid number!')
            print('')
            return self.delete_character()

        # Check for valid number
        if charnum < 1 or charnum > len(clist):
            self.print_error('Please input a number from 1 to %d' % (len(clist)))
            print('')
            return self.delete_character()

        # Grab which character we're talking about
        char = clist[charnum-1]

        # Before confirmation, make sure that the user is not active on
        # any pages.
        pagelist = []
        for page in self.book.pages_sorted():
            if page.character == char:
                pagelist.append(page.pagenum)
        if len(pagelist) > 0:
            print('')
            self.print_error('Character "%s" is the active character on the following pages:' % (char.name))
            for pagenum in pagelist:
                self.print_error('  * %s' % (pagenum))
            print('')
            self.print_error('Refusing to delete character!')
            return

        # This check should never actually resolve to True, but I'm putting it here anyway
        if char == self.cur_char:
            print('')
            self.print_error('Character "%s" is the currently-active character!  Not deleting.' % (char.name))
            return

        # If we get here, we're ready to delete.  Ask for a confirmation
        # even though the stakes are low, given the above checks.
        if self.prompt_yn('Really delete character "%s"' % (char.name), default=False):
            try:
                self.book.delete_character(char.name)
                print('')
                self.print_result('Deleted character "%s"' % (char.name))
            except Exception as e:
                print('')
                self.print_error('Could not delete character: %s' % (e))
        else:
            print('')
            self.print_result('Cancelling deletion')

        return

    def pick_character(self):
        """
        Presents the user with a list of characters to choose
        from.  Returns the character picked (though also sets
        self.cur_char).  Users can also change the current
        character's graphviz coloration through this menu.
        """

        # Show a list of current characters
        print('')
        default = 1
        clist = sorted(self.book.characters.keys())

        # If we have no characters, just force the user into creation mode.
        if len(clist) == 0:
            charnum_txt = 'n'
        else:
            self.print_result('Current Characters:')
            for (idx, cname) in enumerate(clist):
                if ((self.cur_char is not None and cname == self.cur_char.name) or
                    (self.cur_char is None and idx == 0)):
                    print('  [%d] %s (*)' % (idx+1, cname))
                    default = idx+1
                else:
                    print('  [%d] %s' % (idx+1, cname))
            print('')
            print('  [n] New Character')
            print('  [d] Delete Character')
            print('  [e] Edit Character (name, graphviz colors)')
            print('')

            # Have the user pick one
            charnum_txt = self.prompt('Switch to character number [%d]' % (default))

        # If we're told to add a new character, do so!
        if charnum_txt.lower() == 'n':

            # Character name
            newname = self.prompt('New Character Name (enter to cancel)')
            if newname == '':
                return None

            # Now add the character
            try:
                self.cur_char = self.book.add_character(newname)

                # Colors
                default_fontcolor = 'black'
                fontcolor = self.prompt('Text color (for graphviz) [%s]' % (default_fontcolor))
                if fontcolor == '':
                    fontcolor = default_fontcolor
                self.cur_char.fontcolor = fontcolor

                # Colors
                default_fillcolor = 'white'
                fillcolor = self.prompt('Fill color (for graphviz) [%s]' % (default_fillcolor))
                if fillcolor == '':
                    fillcolor = default_fillcolor
                self.cur_char.fillcolor = fillcolor

                # Append to list and set up our charnum
                clist.append(newname)
                charnum = len(clist)

            except Exception as e:
                print('')
                self.print_error('Unable to add new character: %s' % (e))
                return self.pick_character()

        # If we have existing characters and we're told to edit
        # one of them, do so!
        elif len(clist) > 0 and charnum_txt.lower() == 'e':
            return self.edit_character()

        # If we have existing characters and we're told to delete
        # one of them, do so!
        elif len(clist) > 0 and charnum_txt.lower() == 'd':
            return self.delete_character()

        # Just choose our current char if there's no input
        elif charnum_txt == '':
            charnum = default

        # Otherwise, we must (well, should) have a number
        else:
            try:
                charnum = int(charnum_txt)
            except ValueError:
                self.print_error('Please input a valid number!')
                print('')
                return self.pick_character()

        # Check for invalid numbers
        if charnum < 1 or charnum > len(clist):
            self.print_error('Please input a number from 1 to %d' % (len(clist)))
            print('')
            return self.pick_character()

        # Now set our cur_char var, report, and return
        self.cur_char = self.book.characters[clist[charnum-1]]
        print('')
        self.print_result('Picked "%s" as the current character' % (self.cur_char.name))
        return self.cur_char

    def set_page(self, pagenum):
        """
        Sets our book to the specified page, and returns that page.
        Also sets our current character to whoever the page belongs to.
        """
        if pagenum not in self.book.pages:
            raise Exception('Page %s not found!' % (pagenum))
        self.cur_page = self.book.pages[pagenum]
        self.cur_char = self.cur_page.character
        return self.cur_page

    def create_page(self, pagenum):
        """
        Creates a new page and returns it.  Also sets our current
        page.  If the user enters a blank summary, creation will
        be cancelled and None will be returned instead (and the
        current page does not change)
        """
        if pagenum in self.book.pages:
            raise Exception('Page %s already exists!' % (pagenum))

        print('')
        self.print_result('Creating new page %s' % (pagenum))
        summary = self.prompt('Page Summary (enter to cancel)')
        if summary == '':
            return None
        newpage = self.book.add_page(pagenum,
                character=self.cur_char,
                summary=summary)
        self.cur_page = newpage
        return newpage

    def update_summary(self):
        """
        Updates the summary for a page
        """
        print('')
        summary = self.prompt('New Page Summary')
        self.cur_page.summary = summary
        print('')

    def add_choice(self):
        """
        Adds a new choice to the current page. Returns the
        new choice object.  Assume throughout that if the user
        just hits Enter, they want to cancel.
        """
        print('')
        self.print_result('Adding a new choice!')

        # Get the summary
        summary = self.prompt('Summary')
        if summary == '':
            return None

        # And now the target
        target_txt = self.prompt('Target Page Number')
        if target_txt == '':
            return None
        try:
            target = int(target_txt)
        except ValueError:
            if ' ' in target_txt:
                print('')
                self.print_error('Non-numeric page numbers cannot contain spaces!')
                return self.add_choice()
            # Otherwise just let it be a string
            target = target_txt

        try:
            return self.cur_page.add_choice(target, summary)
        except Exception as e:
            # This can happen if the user tries to add a choice to
            # a page that's already linked-to by this page.
            print('')
            self.print_error('Could not add the new choice: %s' % (e))
            return None

    def delete_choice(self):
        """
        Deletes a choice from the current page.
        """
        print('')
        self.print_result('Select a choice to delete:')
        print('')
        choices = self.cur_page.choices_sorted()
        for choice in choices:
            print('  [%s] %s' % (choice.target, choice.summary))
        print('')
        response = self.prompt('Choice to delete (enter to cancel)')
        if response == '':
            return
        else:
            try:
                target = int(response)
            except ValueError:
                # Just let it be a string
                target = response

            try:
                self.cur_page.delete_choice(target)
            except KeyError:
                print('')
                self.print_error('Choice with target of %s not found' % (target))

    def page_switch(self, pagenum=None):
        """
        Switches to a new page.  If the page already exists, we'll
        just switch to it.  If the page does NOT exist, we'll start
        a new one.  Optionally pass in an already-parsed page number
        """
        print('')
        if pagenum is None:
            response = self.prompt('Page Number')
            try:
                pagenum = int(response)
            except ValueError:
                if ' ' in response:
                    print('')
                    self.print_error('Page numbers cannot contain spaces')
                    return None
                pagenum = response

        if self.book.has_intermediate(pagenum):
            print('')
            self.print_error('Page %s is already set as an intermediate page' % (pagenum))
            return None
        elif pagenum in self.book.pages:
            return self.set_page(pagenum)
        else:
            return self.create_page(pagenum)

    def delete_page(self):
        """
        Deletes the given page.  Will refuse to do so if it's the current page.
        """
        print('')
        response = self.prompt('Page Number to delete')
        try:
            pagenum = int(response)
        except ValueError:
            # Just let it be a string
            pagenum = response

        if pagenum == self.cur_page.pagenum:
            print('')
            self.print_error('Refusing to delete current page - switch to a different page')
            return

        # If we got this far, delete the page.
        try:
            self.book.delete_page(pagenum)
        except KeyError:
            print('')
            self.print_error('Page %s not found!' % (pagenum))
            return

        # Report
        print('')
        self.print_result('Page %s deleted!' % (pagenum))

    def add_intermediate(self):
        """
        Adds pages as intermediate.  Will continue prompting until we get
        an empty string.
        """
        while True:
            print('')
            if len(self.book.intermediates) > 0:
                self.print_result('Current intermediates:')
                self.book.print_intermediates(prefix='   ')
                print('')
            response = self.prompt('Page to mark as intermediate (enter to quit)')
            if response == '':
                print('')
                return
            try:
                pagenum = int(response)
            except ValueError:
                # Just let it be a string, even though non-numeric intermediates
                # are a bit pointless.
                pagenum = response
            if pagenum in self.book.pages:
                self.print_error('Page %s is already a "real" page' % (pagenum))
            elif self.book.has_intermediate(pagenum):
                self.print_error('Page %s is already marked as intermediate' % (pagenum))
            else:
                self.book.add_intermediate(pagenum)
                self.print_result('Page %s added as intermediate' % (pagenum))

    def delete_intermediate(self):
        """
        Deletes pages marked as intermediate.  Will continue prompting until
        we get an empty string.
        """
        if len(self.book.intermediates) == 0:
            print('')
            self.print_error('No intermediates are present in the book')
            return

        while len(self.book.intermediates) > 0:
            print('')
            self.print_result('Current intermediates:')
            self.book.print_intermediates(prefix='   ')
            print('')
            response = self.prompt('Intermediate to delete (enter to quit)')
            if response == '':
                print('')
                return
            try:
                try:
                    pagenum = int(response)
                except ValueError:
                    pagenum = response
                self.book.delete_intermediate(pagenum)
            except ValueError:
                print('')
                self.print_error('Invalid page number specified')

    def list_pages(self):
        """
        Lists all the pages we know about, and also various statistics.
        """

        char_counts = {}
        ending_count = 0
        canon_count = 0

        # List our intermediate pages inline with the regular pages,
        # because we can.
        intermediates = self.book.intermediates_sorted()
        cur_intermediate = 0

        print('')
        for page in self.book.pages_sorted():
            # If we have intermediates that come before our page,
            # output them now.
            while ((cur_intermediate < len(intermediates)) and
                (intermediates[cur_intermediate] < page.pagenum)):
                    self.print_intermediates_line('%s - (intermediate page)' % (intermediates[cur_intermediate]))
                    cur_intermediate += 1
            if page.character.name not in char_counts:
                char_counts[page.character.name] = 1
            else:
                char_counts[page.character.name] += 1
            extratext = ''
            if page.ending:
                extratext = '%s - %sENDING%s' % (extratext, self.color_flags(), self.color_reset())
                ending_count += 1
            if page.canonical:
                extratext = '%s - %sCANON%s' % (extratext, self.color_flags(), self.color_reset())
                canon_count += 1
            print('%s - %s (%s)%s' % (page.pagenum, page.summary, page.character.name, extratext))
        for intermediate in intermediates[cur_intermediate:]:
            self.print_intermediates_line('%s - (intermediate page)' % (intermediates[cur_intermediate]))
        print('')
        self.print_result('Total pages known: %d' % (len(self.book.pages)))
        self.print_result('Canon Pages: %s' % (canon_count))
        self.print_result('Ending Pages: %s' % (ending_count))
        if len(self.book.intermediates) > 0:
            self.print_result('Intermediate Pages: %s' % (len(self.book.intermediates)))
        self.print_result('Character Counts:')
        for (char, count) in [(name, char_counts[name]) for name in sorted(char_counts.keys())]:
            if count == 1:
                plural = ''
            else:
                plural = 's'
            self.print_result('  %s: %d page%s' % (char, count, plural))
        print('')

        # Also, what the heck.  Let's go ahead and make a list of all pages
        # that we've MISSED in here.  Mostly useful for doublechecking things
        # if you think you're basically done with the book.
        missing = []
        # This is ridiculous, but: unique real+intermediate pages, filtered
        # to ensure that there's ony numeric entries, since we have non-
        # numeric pages now.
        pages = sorted([x for x in set(self.book.pages.keys() + self.book.intermediates.keys()) if isinstance(x, int)])
        last_page = pages[-1]
        total_pages = range(1,last_page+1)
        for page in reversed(pages):
            del total_pages[page-1]
        if len(total_pages) < 20:
            print('Missing pages (%d total):' % (len(total_pages)))
            print(total_pages)
            print('')

    def save(self):
        """
        Saves out to our filename
        """

        self.book.save()
        self.print_result('Saved to %s' % (self.book.filename))

    def toggle_canonical(self):
        """
        Toggles the canonical status of the current page
        """
        self.cur_page.toggle_canonical()

    def toggle_ending(self):
        """
        Toggles the 'ending' status of the current page
        """
        self.cur_page.toggle_ending()

    def generate_graphviz(self):
        """
        User-requested generation of Graphviz DOT file.
        """

        # Construct our default filename to use
        filename_parts = self.filename.split('.')
        default_file = '%s.dot' % (filename_parts[0])

        # Get a filename from the user
        print('')
        filename = self.prompt('Filename for Graphviz DOT export [%s]' % (default_file))
        if filename == '':
            filename = default_file

        # Check to make sure that we're not overwriting ourselves.
        # This is pretty silly, but whatever.
        if filename == self.filename:
            print('')
            self.print_error('ERROR: Refusing to write DOT file on top of book data YAML file.')
            return 1

        # Actually do the export, and try running graphviz to boot.
        if self.export_dot(filename):
            filename_parts = filename.split('.')
            png_file_default = '%s.png' % (filename_parts[0])
            png_file = self.prompt('Filename for Graphviz PNG output [%s]' % (png_file_default))
            if png_file == '':
                png_file = png_file_default
            if png_file == self.filename:
                print('')
                self.print_error('ERROR: Refusing to write PNG on top of book data YAML file.')
                return 1
            if os.path.exists(png_file):
                print('')
                response = self.prompt_yn('File "%s" already exists.  Overwrite' % (png_file))
                if not response:
                    return 1
            print('')
            self.print_result('Attempting to generate %s' % (png_file))
            try:
                retval = subprocess.call(['dot', '-Tpng', filename, '-o', png_file])
                print('')
                if retval == 0:
                    self.print_result('PNG Graph generated to %s' % (png_file))
                else:
                    self.print_error('Error generating PNG, you will have to generate that yourself')
            except OSError:
                print('')
                self.print_error('Graphviz "dot" executable not found, you will have to generate the PNG yourself')

    def export_dot(self, dot_filename):
        """
        Export our book to a Graphviz DOT file, using the
        passed-in dot_filename.
        """

        # Check to see if the filename exists already
        if os.path.exists(dot_filename):
            response = self.prompt_yn('File "%s" already exists.  Overwrite' % (dot_filename))
            if not response:
                return False

        book = self.book
        fileparts = dot_filename.split('.')
        with open(dot_filename, 'w') as df:
            df.write("digraph %s {\n" % (fileparts[0]))

            # Set up a structure to hold page definitions simultaneously
            # for pages we've visited, and pages we haven't.  That way
            # the "known" path won't veer off the left so much, or at
            # least if it does so it'll only be by chance instead of
            # design.
            all_pages = {}

            # First up - Visited pages!
            for page in book.pages_sorted():
                labelstr = 'label="Page %s - %s"' % (
                    page.pagenum,
                    page.summary.replace('"', '\\"')
                )
                styles = ['filled']
                if page.canonical:
                    labelstr = '%s shape=box' % (labelstr)
                    styles.append('bold')
                if page.ending:
                    labelstr = '%s fontcolor=white fillcolor=azure4' % (labelstr)
                else:
                    labelstr = '%s fontcolor=%s fillcolor=%s' % (labelstr,
                        page.character.fontcolor,
                        page.character.fillcolor)
                if len(styles) > 0:
                    labelstr = '%s style="%s"' % (labelstr, ','.join(styles))
                all_pages[page.pagenum] = labelstr

            # Unvisited pages
            unknown_pages = {}
            for page in book.pages_sorted():
                for choice in page.choices_sorted():
                    if choice.target not in book.pages:
                        if choice.target in unknown_pages:
                            print('NOTICE: Overwriting existing not-visited link for page %s' % (choice.target))
                        unknown_pages[choice.target] = '(Page %s - %s)' % (choice.target, choice.summary.replace('>', '').replace('<', ''))
            for (page, text) in unknown_pages.items():
                all_pages[page] = 'label=<<i>%s</i>>' % (text)

            # Now aggregate all our pages together
            df.write("\n");
            df.write("\t// Pages\n");
            for pagenum in sorted(all_pages.keys()):
                df.write("\t%s [%s];\n" % (pagenum, all_pages[pagenum]))

            # Choices!
            df.write("\n");
            df.write("\t// Choices\n");
            for page in book.pages_sorted():
                for choice in page.choices_sorted():
                    df.write("\t%s -> %s;\n" % (page.pagenum, choice.target))
            df.write("\n");
            df.write("}\n")

        return True

    def run(self):
        """
        Runs our actual app.  Should be exciting!
        """

        # First check if we're doing something non-interactive
        if self.do_dot:
            self.book = Book.load(self.filename)
            return self.export_dot(self.do_dot)
        
        self.print_heading('Chooseable-Path Adventure Tracker')
        print('')

        if not os.path.exists(self.filename):
            self.print_error('"%s" does not exist' % (self.filename))
            if not self.prompt_yn('Continue as a new book'):
                self.print_error('Exiting!')
                return 1

            # Creating a new book at this point
            print('')
            newtitle = self.prompt('Book Title (enter to cancel)')
            if newtitle == '':
                self.print_error('Cancelling book creation!')
                return 1
            self.book = Book(newtitle, filename=self.filename)

            # Pick a character (which at this point would just create
            # a new character)
            if not self.pick_character():
                self.print_error('Cancelling book creation!')
                return 1

            # Create the initial room
            while self.cur_page is None:
                self.create_page(1)

            # Aaand save it out right away, for good measure
            self.save()

        else:

            # Load an existing book
            self.book = Book.load(self.filename)
            self.set_page(1)

            self.print_result('Loaded Book "%s"' % (self.book.title))

        # At this point we have a book set up and loaded.  Time to get going!
        OPT_QUIT = 'q'
        OPT_CHAR = 'c'
        OPT_SAVE = 's'
        OPT_CHOICE = 'a'
        OPT_DEL = 'd'
        OPT_PAGE = 'p'
        OPT_DELPAGE = 'x'
        OPT_LISTPAGE = 'l'
        OPT_SUMMARY = 'u'
        OPT_CANON = 't'
        OPT_ENDING = 'e'
        OPT_GRAPHVIZ = 'g'
        OPT_INTERMEDIATE = 'i'
        OPT_INTER_DEL = 'o'
        OPT_COLOR = 'r'
        
        while True:
            
            # Status display
            print('')
            self.print_heading('='*80)
            if self.cur_page.canonical:
                self.print_flags('**** CANON ****')
            if self.cur_page.ending:
                self.print_flags('**** THE END ****')
            self.print_result('Current Page: %s' % (self.cur_page.pagenum))
            self.print_result('Current Character: %s' % (self.cur_char.name))
            print('')
            print('Summary: %s' % (self.cur_page.summary))
            if len(self.cur_page.choices) > 0:
                print('')
                for choice in self.cur_page.choices_sorted():
                    reports = []
                    extratext = ''
                    try:
                        remote_page = self.book.get_page(choice.target)
                        reports.append('visited')
                        if remote_page.canonical:
                            reports.append('CANON')
                        if remote_page.ending:
                            reports.append('ENDING')
                    except KeyError:
                        pass
                    if len(reports) > 0:
                        extratext = ' (%s)' % (', '.join(['%s%s%s' % (self.color_flags(), text, self.color_reset()) for text in reports]))
                    print('  Page %s - %s%s' % (choice.target, choice.summary, extratext))
            self.print_heading('='*80)
            self.print_commands('[%s] Add Choice [%s] Delete Choice [%s] Character' %(
                    OPT_CHOICE, OPT_DEL, OPT_CHAR))
            self.print_commands('[%s/##] Page [%s] Delete Page [%s] List Pages [%s] Update Summary' % (
                    OPT_PAGE, OPT_DELPAGE, OPT_LISTPAGE, OPT_SUMMARY))
            self.print_commands('[%s] Toggle Canonical [%s] Toggle Ending' % (
                    OPT_CANON, OPT_ENDING))
            self.print_commands('[%s] Add Intermediate [%s] Delete Intermediate' % (
                    OPT_INTERMEDIATE, OPT_INTER_DEL))
            if self.has_colorama:
                extracommands = ' [%s] Swap Color Style' % (OPT_COLOR)
            else:
                extracommands = ''
            self.print_commands('[%s] Save [%s] Graphviz [%s] Quit%s' % (
                    OPT_SAVE, OPT_GRAPHVIZ, OPT_QUIT, extracommands))

            # User input
            response = self.prompt('Action')
            print('')
            try:
                pagenum = int(response)
                self.page_switch(pagenum)
            except ValueError:
                option = response.lower()
                if option == OPT_CHAR:
                    self.pick_character()
                    self.cur_page.character = self.cur_char
                elif option == OPT_CHOICE:
                    self.add_choice()
                elif option == OPT_DEL:
                    self.delete_choice()
                elif option == OPT_PAGE:
                    self.page_switch()
                elif option == OPT_DELPAGE:
                    self.delete_page()
                elif option == OPT_LISTPAGE:
                    self.list_pages()
                elif option == OPT_SUMMARY:
                    self.update_summary()
                elif option == OPT_CANON:
                    self.toggle_canonical()
                elif option == OPT_ENDING:
                    self.toggle_ending()
                elif option == OPT_GRAPHVIZ:
                    self.generate_graphviz()
                elif option == OPT_SAVE:
                    self.save()
                elif option == OPT_INTERMEDIATE:
                    self.add_intermediate()
                elif option == OPT_INTER_DEL:
                    self.delete_intermediate()
                elif option == OPT_COLOR and self.has_colorama:
                    self.set_color()
                elif option == OPT_QUIT:
                    print('')
                    if self.prompt_yn('Save before quitting'):
                        self.save()
                    return 0
                else:
                    print('')
                    self.print_error('Unknown option, try again!')

        # Shouldn't be any way to get here, actually.
        return 0
        
if __name__ == '__main__':
    app = App()
    sys.exit(app.run())
