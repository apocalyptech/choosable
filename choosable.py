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
        print('  %s -> %d' % (self.summary, self.target))

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
            raise Exception('Character "%s" not found for page %d' % (pagedict['character'], pagedict['pagenum']))
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
        print('Page %d (%s) - %s' % (self.pagenum, self.character.name, self.summary))
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
            raise Exception('Target %d already exists on page %d' % (choice.target, self.pagenum))

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

    def save(self, filename=None, verbose=True):
        """
        Saves out the book.  In YAML, I guess?  If verbose
        is False, we won't spit out any text to the console
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

        # And report, if necesssary
        if verbose:
            print('Saved to %s' % (filename))

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
            raise Exception('Page %d already exists' % (page.pagenum))
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

    def __init__(self):

        self.book = None
        self.cur_char = None
        self.cur_page = None

        # Parse arguments
        parser = argparse.ArgumentParser(description='Chooseable-Path Adventure Tracker')
        parser.add_argument('-f', '--filename',
            required=True,
            type=str,
            help='Filename to load or create')
        parser.add_argument('-d', '--dot',
            type=str,
            metavar='DOTFILE',
            help='Output a graphviz DOT file instead of interactively editing')
        args = parser.parse_args()

        # Store the data we care about
        self.filename = args.filename
        self.do_dot = args.dot

    def prompt(self, prompt_text):
        """
        Prompts a user for input.  A simple wrapper.
        """
        sys.stdout.write('%s: ' % (prompt_text))
        sys.stdout.flush()
        return sys.stdin.readline().strip()

    def prompt_yn(self, prompt_text, default=True):
        """
        Prompts for a user for input and assumes that it's a
        yes/no question.  Returns True or False, rather than
        the actual text.  The default response defaults to
        Yes but pass in default to change.

        I suspect my logic when default=False is probably
        wrong somehow, but we're not actually using that yet.
        """
        if default == True:
            optstr = 'Y|n'
        else:
            optstr = 'y|N'
        sys.stdout.write('%s [%s]? ' % (prompt_text, optstr))
        sys.stdout.flush()
        user_input = sys.stdin.readline().strip()
        if user_input == '':
            return default
        else:
            user_input = user_input[:1].lower()
            if default == True:
                return (user_input == 'y')
            else:
                return (user_input == 'n')

    def pick_character(self):
        """
        Presents the user with a list of characters to choose
        from.  Returns the character picked (though also sets
        self.cur_char)
        """

        # Show a list of current characters
        print('')
        print('Current Characters:')
        default = 1
        clist = sorted(self.book.characters.keys())
        for (idx, cname) in enumerate(clist):
            if ((self.cur_char is not None and cname == self.cur_char.name) or
                (self.cur_char is None and idx == 0)):
                print('  [%d] %s (*)' % (idx+1, cname))
                default = idx+1
            else:
                print('  [%d] %s' % (idx+1, cname))
        if len(clist) == 0:
            print('  [1] (new character) (*)')
        else:
            print('  [%d] (new character)' % (len(clist)+1))
        print('')

        # Have the user pick one
        charnum_txt = self.prompt('Switch to character number [%d]' % (default))
        if charnum_txt == '':
            charnum = default
        else:
            try:
                charnum = int(charnum_txt)
            except ValueError:
                print('Please input a valid number!')
                print('')
                return self.pick_character()

        # Check for invalid numbers
        if charnum < 1 or charnum > len(clist)+1:
            print('Please input a number from 1 to %d' % (len(clist)+1))
            print('')
            return self.pick_character()

        # The last option is always to add a new character
        if charnum == len(clist)+1:
            newname = self.prompt('New Character Name')
            try:
                self.cur_char = self.book.add_character(newname)
                clist.append(newname)
            except Exception as e:
                print('')
                print('Unable to add new character: %s' % (e))
                return self.pick_character()

        # Now set our cur_char var, report, and return
        self.cur_char = self.book.characters[clist[charnum-1]]
        print('Picked "%s" as the current character' % (self.cur_char.name))
        return self.cur_char

    def set_page(self, pagenum):
        """
        Sets our book to the specified page, and returns that page.
        Also sets our current character to whoever the page belongs to.
        """
        if pagenum not in self.book.pages:
            raise Exception('Page %d not found!' % (pagenum))
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
            raise Exception('Page %d already exists!' % (pagenum))

        print('')
        print('Creating new page %d' % (pagenum))
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
        print('Adding a new choice!')

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
            print('')
            print('Please input a valid number!')
            return self.add_choice()
        try:
            return self.cur_page.add_choice(target, summary)
        except Exception as e:
            # This can happen if the user tries to add a choice to
            # a page that's already linked-to by this page.
            print('')
            print('Could not add the new choice: %s' % (e))
            return None

    def delete_choice(self):
        """
        Deletes a choice from the current page.
        """
        print('')
        print('Select a choice to delete:')
        print('')
        choices = self.cur_page.choices_sorted()
        for choice in choices:
            print('  [%d] %s' % (choice.target, choice.summary))
        print('')
        response = self.prompt('Choice to delete (enter to cancel)')
        if response == '':
            return
        else:
            try:
                target = int(response)
            except ValueError:
                print('')
                print('Invalid number, cancelling!')
                return
            try:
                self.cur_page.delete_choice(target)
            except KeyError:
                print('')
                print('Choice with target of %d not found' % (target))

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
                print('')
                print('Invalid page number specified')
                return None

        if self.book.has_intermediate(pagenum):
            print('')
            print('Page %d is already set as an intermediate page' % (pagenum))
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
            print('')
            print('Invalid page number specified')
            return

        if pagenum == self.cur_page.pagenum:
            print('')
            print('Refusing to delete current page - switch to a different page')
            return

        # If we got this far, delete the page.
        try:
            self.book.delete_page(pagenum)
        except KeyError:
            print('')
            print('Page %d not found!' % (pagenum))
            return

        # Report
        print('')
        print('Page %d deleted!' % (pagenum))

    def add_intermediate(self):
        """
        Adds pages as intermediate.  Will continue prompting until we get
        an empty string.
        """
        print('')
        while True:
            response = self.prompt('Page to mark as intermediate (enter to quit)')
            if response == '':
                print('')
                return
            try:
                pagenum = int(response)
                if pagenum in self.book.pages:
                    print('Page %d is already a "real" page' % (pagenum))
                elif self.book.has_intermediate(pagenum):
                    print('Page %d is already marked as intermediate' % (pagenum))
                else:
                    self.book.add_intermediate(pagenum)
                    print('Page %d added as intermediate' % (pagenum))
            except ValueError:
                print('')
                print('Invalid page number specified!')

    def delete_intermediate(self):
        """
        Deletes pages marked as intermediate.  Will continue prompting until
        we get an empty string.
        """
        if len(self.book.intermediates) == 0:
            print('')
            print('No intermediates are present in the book')
            return

        while len(self.book.intermediates) > 0:
            print('')
            print('Current intermediates:')
            self.book.print_intermediates(prefix='   ')
            print('')
            response = self.prompt('Intermediate to delete (enter to quit)')
            if response == '':
                print('')
                return
            try:
                pagenum = int(response)
                self.book.delete_intermediate(pagenum)
            except ValueError:
                print('')
                print('Invalid page number specified')

    def list_pages(self):
        """
        Lists all the pages we know about, and also various statistics.
        """

        char_counts = {}
        ending_count = 0
        canon_count = 0

        print('')
        for page in self.book.pages_sorted():
            if page.character.name not in char_counts:
                char_counts[page.character.name] = 1
            else:
                char_counts[page.character.name] += 1
            if page.ending:
                ending_count += 1
            if page.canonical:
                extratext = ' - CANON'
                canon_count += 1
            else:
                extratext = ''
            print('%d - %s (%s)%s' % (page.pagenum, page.summary, page.character.name, extratext))
        print('')
        print('Total pages known: %d' % (len(self.book.pages)))
        print('Canon Pages: %s' % (canon_count))
        print('Ending Pages: %s' % (ending_count))
        if len(self.book.intermediates) > 0:
            print('Intermediate Pages: %s' % (len(self.book.intermediates)))
        print('Character Counts:')
        for (char, count) in [(name, char_counts[name]) for name in sorted(char_counts.keys())]:
            if count == 1:
                plural = ''
            else:
                plural = 's'
            print('  %s: %d page%s' % (char, count, plural))
        print('')

        # Also, what the heck.  Let's go ahead and make a list of all pages
        # that we've MISSED in here.  Mostly useful for doublechecking things
        # if you think you're basically done with the book.
        missing = []
        pages = sorted(set(self.book.pages.keys() + self.book.intermediates.keys()))
        last_page = pages[-1]
        total_pages = range(1,last_page+1)
        for page in reversed(pages):
            del total_pages[page-1]
        if len(total_pages) < 20:
            print('Missing pages (%d total):' % (len(total_pages)))
            print(total_pages)
            print('')

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
            print('ERROR: Refusing to write DOT file on top of book data YAML file.')
            return 1

        # Actually do the export
        return self.export_dot(filename)

    def export_dot(self, dot_filename):
        """
        Export our book to a Graphviz DOT file, using the
        passed-in dot_filename.
        """

        # Check to see if the filename exists already
        if os.path.exists(dot_filename):
            response = self.prompt_yn('File "%s" already exists.  Overwrite' % (dot_filename))
            if not response:
                return 1

        book = self.book
        fileparts = dot_filename.split('.')
        with open(dot_filename, 'w') as df:
            df.write("digraph %s {\n" % (fileparts[0]))
            df.write("\n");

            # Set up a structure to hold page definitions simultaneously
            # for pages we've visited, and pages we haven't.  That way
            # the "known" path won't veer off the left so much, or at
            # least if it does so it'll only be by chance instead of
            # design.
            all_pages = {}

            # First up - Visited pages!
            df.write("\t// Visited Pages\n");
            for page in book.pages_sorted():
                labelstr = 'label="Page %d - %s"' % (
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
                            print('NOTICE: Overwriting existing not-visited link for page %d' % (choice.target))
                        unknown_pages[choice.target] = '(Page %d - %s)' % (choice.target, choice.summary.replace('>', '').replace('<', ''))
            for (page, text) in unknown_pages.items():
                all_pages[page] = 'label=<<i>%s</i>>' % (text)

            # Now aggregate all our pages together
            df.write("\n");
            df.write("\t// Pages\n");
            for pagenum in sorted(all_pages.keys()):
                df.write("\t%d [%s];\n" % (pagenum, all_pages[pagenum]))

            # Choices!
            df.write("\n");
            df.write("\t// Choices\n");
            for page in book.pages_sorted():
                for choice in page.choices_sorted():
                    df.write("\t%d -> %d;\n" % (page.pagenum, choice.target))
            df.write("\n");
            df.write("}\n")

        return 0

    def run(self):
        """
        Runs our actual app.  Should be exciting!
        """

        # First check if we're doing something non-interactive
        if self.do_dot:
            self.book = Book.load(self.filename)
            return self.export_dot(self.do_dot)
        
        print('Chooseable-Path Adventure Tracker')
        print('')

        if not os.path.exists(self.filename):
            print('"%s" does not exist' % (self.filename))
            if not self.prompt_yn('Continue as a new book'):
                print('Exiting!')
                return 1

            # Creating a new book at this point
            print('')
            newtitle = self.prompt('Book Title')
            self.book = Book(newtitle, filename=self.filename)

            # Pick a character (which at this point would just create
            # a new character)
            self.pick_character()

            # Create the initial room
            while self.cur_page is None:
                self.create_page(1)

            # Aaand save it out right away, for good measure
            self.book.save()

        else:

            # Load an existing book
            self.book = Book.load(self.filename)
            self.set_page(1)

            print('Loaded Book "%s"' % (self.book.title))

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
        
        while True:
            
            # Status display
            print('')
            print('-'*80)
            if self.cur_page.canonical:
                print('**** CANON ****')
            if self.cur_page.ending:
                print('**** THE END ****')
            print('Current Page: %d' % (self.cur_page.pagenum))
            print('Current Character: %s' % (self.cur_char.name))
            print('')
            print('Summary: %s' % (self.cur_page.summary))
            if len(self.cur_page.choices) > 0:
                print('')
                for choice in self.cur_page.choices_sorted():
                    extratext = ''
                    try:
                        remote_page = self.book.get_page(choice.target)
                        extratext = '%s - visited' % (extratext)
                        if remote_page.canonical:
                            extratext = '%s (CANON)' % (extratext)
                    except KeyError:
                        pass
                    print('  %s (turn to page %d%s)' % (choice.summary, choice.target, extratext))
            print('-'*80)
            print('[%s] Add Choice [%s] Delete Choice [%s] Character' %(
                    OPT_CHOICE, OPT_DEL, OPT_CHAR))
            print('[%s/##] Page [%s] Delete Page [%s] List Pages [%s] Update Summary' % (
                    OPT_PAGE, OPT_DELPAGE, OPT_LISTPAGE, OPT_SUMMARY))
            print('[%s] Toggle Canonical [%s] Toggle Ending' % (
                    OPT_CANON, OPT_ENDING))
            print('[%s] Add Intermediate [%s] Delete Intermediate' % (
                    OPT_INTERMEDIATE, OPT_INTER_DEL))
            print('[%s] Save [%s] Graphviz [%s] Quit' % (
                    OPT_SAVE, OPT_GRAPHVIZ, OPT_QUIT))

            # User input
            response = self.prompt('Action')
            print('')
            try:
                pagenum = int(response)
                self.page_switch(pagenum)
            except ValueError:
                option = response[:1].lower()
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
                    self.book.save()
                elif option == OPT_INTERMEDIATE:
                    self.add_intermediate()
                elif option == OPT_INTER_DEL:
                    self.delete_intermediate()
                elif option == OPT_QUIT:
                    print('')
                    if self.prompt_yn('Save before quitting'):
                        self.book.save()
                    return 0
                else:
                    print('')
                    print('Unknown option, try again!')

        # Shouldn't be any way to get here, actually.
        return 0
        
if __name__ == '__main__':
    app = App()
    sys.exit(app.run())
