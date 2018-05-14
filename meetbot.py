#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Simple Bot to reply to Telegram messages
# This program is dedicated to the public domain under the CC0 license.
"""
This Bot uses the Updater class to handle the bot.

First, a few callback functions are defined. Then, those functions are passed to
the Dispatcher and registered at their respective places.
Then, the bot is started and runs until we press Ctrl-C on the command line.

Usage:
Example of a bot-user conversation using ConversationHandler.
Send /start to initiate the conversation.
Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""
import os
import sys

from telegram import (ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode,
                      CallbackQuery, ChosenInlineResult, InlineQuery, InlineQueryResult, InlineQueryResultArticle,
                      InputMessageContent, InputTextMessageContent)
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters, RegexHandler,
                          ConversationHandler, CallbackQueryHandler, ChosenInlineResultHandler,
                          InlineQueryHandler)


# from survey import Survey

import logging
import sqlite3
import ConfigParser

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

TITLE, DESCRIPTION, SETTINGS, OPTIONS = range(4)

settings_keyboard = [['YES/NO', 'YES/MAYBE/NO']]

import time, threading, pickle


class SurveyOption:
    id = 0
    text = ""
    yes = 0
    maybe = 0
    no = 0

    def __init__(self, id, text):
        self.id = id
        self.text = text

    def setYes(self, yes):
        self.yes = yes

    def setMaybe(self, maybe):
        self.maybe = maybe

    def setNo(self, no):
        self.no = no

    def getYes(self):
        return self.yes

    def getText(self):
        return self.text

    def getMaybe(self):
        return self.maybe

    def getNo(self):
        return self.no

    # def __str__(self):
    # return "SurveyOption[id=%s,text='%s',yes=%s,maybe=%s,no=%s]" % (id, text, yes, maybe, no)


def lastSurveyForUser(userid):
    try:

        conn = sqlite3.connect('meetbot.db')
        c = conn.cursor()
        t = (userid,)
        c.execute(
            'SELECT ROWID,user_id,title,description,setting_maybe FROM surveys WHERE user_id=? ORDER BY ROWID DESC', t)
        s = c.fetchone()
        if (s == None):
            logger.info("Request of survey for unknown user: %s", userid)

        conn.close()
    except Exception as e:
        logger.warning("failed to retrieve survey: %s", e)
    return s


def getSurveyById(survey_id):
    try:

        conn = sqlite3.connect('meetbot.db')
        c = conn.cursor()
        t = (survey_id,)
        c.execute(
            'SELECT ROWID,user_id,title,description,setting_maybe FROM surveys WHERE ROWID=? ORDER BY ROWID DESC', t)
        s = c.fetchone()
        conn.close()
        if (s == None):
            logger.info("No survey with id %s found", t)
            return None


    except Exception as e:
        logger.warning("failed to retrieve survey: %s", e)
    return s


def getSurveyOptions(survey):
    try:
        conn = sqlite3.connect('meetbot.db')
        c = conn.cursor()
        options = []
        for row in c.execute('''SELECT ROWID,option FROM survey_options WHERE survey_id=?''', (survey[0],)):
            options.append(SurveyOption(row[0], row[1]))

    except Exception as e:
        logger.warning("failed to retrieve options: %s", e)
    return options


def getOptionVotes(option):
    conn = sqlite3.connect('meetbot.db')
    c = conn.cursor()
    c.execute(
        'SELECT sum(yes), sum(maybe), sum(no) FROM option_votes WHERE option_id = ?', (option.id,))
    nums = c.fetchone()
    logger.info("Current counts: %s, %s, %s" % (nums[0], nums[1], nums[2]))
    option.setYes(nums[0])
    option.setMaybe(nums[1])
    option.setNo(nums[2])
    return option


def build_menu(buttons,
               n_cols,
               header_buttons=None,
               footer_buttons=None):
    menu = [buttons[i:i + n_cols] for i in range(0, len(buttons), n_cols)]
    if header_buttons:
        menu.insert(0, header_buttons)
    if footer_buttons:
        menu.append(footer_buttons)
    return menu


def start(bot, update):
    update.message.reply_text(
        'Hi! This is a bot to setup a survey for a meeting date.'
        'Type /new for a new survey'
    )

    return ConversationHandler.END


def new(bot, update):
    global survey_id
    t = (update.message.from_user.id,)
    conn = sqlite3.connect('meetbot.db')
    c = conn.cursor()
    c.execute('''SELECT * FROM users WHERE user_id=?''', t)
    user = c.fetchone()
    if (user == None):
        try:
            u = (update.message.from_user.id, update.message.from_user.username, update.message.from_user.first_name,)
            logger.info("Storing new User: %s, %s, %s", update.message.from_user.id, update.message.from_user.username,
                        update.message.from_user.first_name)
            num = c.execute('''INSERT INTO users VALUES (?,?,?)''', u).rowcount
            logger.info("New user_id: %d", update.message.from_user.id)
        except Exception as e:
            logger.warning("failed to insert: ", e)

    c.execute('''INSERT INTO surveys (user_id) VALUES (?)''', t)
    sid = c.lastrowid
    conn.commit()
    conn.close()
    logger.info("New Survey with id: %d", sid)
    update.message.reply_text(
        'Send me a title for the survey. You can cancel the creation with /cancel')

    return TITLE


def title(bot, update):
    user = update.message.from_user
    s = lastSurveyForUser(user.id)
    if (s != None):
        sid = s[0]
        conn = sqlite3.connect('meetbot.db')
        c = conn.cursor()
        c.execute('UPDATE surveys SET title = ? WHERE ROWID=?', (update.message.text, sid))
        conn.commit()
        conn.close()
    logger.info("Title of Survey: %s", update.message.text)
    update.message.reply_text('Now send me a description, '
                              ' or send /skip if you don\'t want to.',
                              reply_markup=ReplyKeyboardRemove())

    return DESCRIPTION


def description(bot, update):
    user = update.message.from_user
    s = lastSurveyForUser(user.id)
    if (s != None):
        sid = s[0]
        conn = sqlite3.connect('meetbot.db')
        c = conn.cursor()
        c.execute('UPDATE surveys SET description = ? WHERE ROWID=?', (update.message.text, sid,))
        conn.commit()
        conn.close()
    logger.info("Description of %s: %s", user.first_name, update.message.text)
    update.message.reply_text('OK. Now select some settings.\n'
                              'Should the user have a maybe option?',
                              reply_markup=ReplyKeyboardMarkup(settings_keyboard, one_time_keyboard=True))

    return SETTINGS


def skip_description(bot, update):
    user = update.message.from_user
    logger.info("No description of %s", user.first_name)
    update.message.reply_text('OK, no description. Now select some settings.\n'
                              'Should the user have a maybe option?',
                              reply_markup=ReplyKeyboardMarkup(settings_keyboard, one_time_keyboard=True))

    return SETTINGS


def settings_maybe(bot, update):
    user = update.message.from_user
    s = lastSurveyForUser(user.id)
    if (s != None):
        sid = s[0]
        conn = sqlite3.connect('meetbot.db')
        c = conn.cursor()
        if (update.message.text == 'YES/NO'):
            c.execute('UPDATE surveys SET setting_maybe = ? WHERE ROWID=?', (False, sid))
            update.message.reply_text('Users will have to choose between yes and no.\n'
                                      'Now give up to 10 vote options.',
                                      reply_markup=ReplyKeyboardRemove())
        else:
            c.execute('UPDATE surveys SET setting_maybe = ? WHERE ROWID=?', (True, sid))
            update.message.reply_text('Users will have to choose between yes, maybe and no.\n'
                                      'Now give up to 10 vote options.',
                                      reply_markup=ReplyKeyboardRemove())

    conn.commit()
    conn.close()

    return OPTIONS


def option(bot, update):
    user = update.message.from_user
    logger.info("User %s gave following option: %s", user.first_name, update.message.text)
    s = lastSurveyForUser(user.id)
    if (s != None):
        sid = s[0]
        conn = sqlite3.connect('meetbot.db')
        c = conn.cursor()
        c.execute('INSERT INTO survey_options (survey_id,option) VALUES (?,?)', (sid, update.message.text))
        c.execute('''SELECT COUNT(*) FROM survey_options WHERE survey_id = ?''', (sid,))
        num = c.fetchone()[0]
        logger.info("There are %s options for this survey", num)
        if (num == 10):
            update.message.reply_text('OK, 10 options is enough. You are finished-')
            displaySurvey(bot, s, user.id)
            conn.commit()
            conn.close()
            return ConversationHandler.END
        else:
            update.message.reply_text('OK, give another option or finish with /end.')
            conn.commit()
            conn.close()
    return OPTIONS


def end(bot, update):
    user = update.message.from_user
    logger.info("completed of %s", user.first_name)
    update.message.reply_text('Thank you! I hope we can talk again some day.')
    s = lastSurveyForUser(user.id)
    displaySurvey(bot, s, user.id)

    return ConversationHandler.END


def cancel(bot, update):
    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.first_name)
    update.message.reply_text('Bye! I hope we can talk again some day.',
                              reply_markup=ReplyKeyboardRemove())

    return ConversationHandler.END


def surveyText(s):
    return ('*%s*\n%s\n' % (s[2], s[3]))


def displaySurvey(bot, s, chat_id):
    if (s[4] == 1):
        cols = 3
    else:
        cols = 2
    msgtext = surveyText(s)
    so = getSurveyOptions(s)
    survey_buttons = []
    survey_buttons.append(InlineKeyboardButton("Share", switch_inline_query="survey-%s" % s[0]))
    bot.send_message(chat_id=chat_id, text=msgtext,
                     parse_mode=ParseMode.MARKDOWN,
                     reply_markup=InlineKeyboardMarkup(
                         build_menu(survey_buttons, n_cols=1)))
    button_list = []
    for opt in so:
        opt = getOptionVotes(opt)


        msgtext = '''*%s*: %s yes, ''' % (opt.text, opt.yes)
        if (s[4] == 1):
            msgtext += '''%s maybe, ''' % opt.maybe
        msgtext += '''%s no\n''' % opt.no

        button_list.append(
            InlineKeyboardButton("YES (%s)" % opt.getYes(), callback_data=('%s-%s-yes' % (s[0], opt.id))))
        if (s[4] == 1):
            button_list.append(
                InlineKeyboardButton("MAYBE (%s)" % opt.getMaybe(), callback_data=('%s-%s-maybe' % (s[0], opt.id))))
        button_list.append(InlineKeyboardButton("NO (%s)" % opt.getNo(), callback_data=('%s-%s-no' % (s[0], opt.id))))
        bot.send_message(chat_id=chat_id, text=msgtext,
                         reply_markup=InlineKeyboardMarkup(build_menu(button_list, n_cols=cols)),
                         parse_mode=ParseMode.MARKDOWN)


def checkUserExistence(user):
    conn = sqlite3.connect('meetbot.db')
    c = conn.cursor()
    res = c.execute('''SELECT * FROM users WHERE user_id = ?''', (user.id,))
    if (len(res.fetchall()) == 0):
        c.execute('''INSERT INTO users values (?,?,?,?)''', (user.id, user.username, user.first_name, user.last_name))
    else:
        c.execute('''UPDATE users SET username = ?, first_name = ?, name = ? WHERE user_id = ?''',
                  (user.username, user.first_name, user.name, user.id))
    conn.commit()
    conn.close()


def updateVote(bot, update, user_data):
    callbackQuery = update.callback_query

    conn = sqlite3.connect('meetbot.db')
    c = conn.cursor()
    user = callbackQuery.from_user
    checkUserExistence(user)
    data = callbackQuery.data
    survey_id, option_id, vote = data.split("-")
    s = getSurveyById(survey_id)
    logger.info("%s voted for %s on option %s" % (user.username, vote, option_id))
    # check old votes
    c.execute(
        'SELECT ROWID,yes,maybe,no FROM option_votes WHERE user_id=? AND option_id = ? ORDER BY ROWID DESC',
        (user.id, option_id))
    res = c.fetchall()
    logger.info("user has already %s on that survey option" % len(res))
    if (len(res) == 1):
        voteresult = res[0]
        if (vote == "yes"):
            yes = voteresult[1] + 1
            maybe = 0
            no = 0
        if (vote == "maybe"):
            yes = 0
            maybe = voteresult[2] + 1
            no = 0
        if (vote == "no"):
            yes = 0
            maybe = 0
            no = voteresult[3] + 1
        c.execute('''UPDATE option_votes SET yes = ?, maybe = ?, no = ? WHERE ROWID = ?''',
                  (yes, maybe, no, voteresult[0]))
    else:
        if (vote == "yes"):
            yes = 1
            maybe = 0
            no = 0
        if (vote == "maybe"):
            yes = 0
            maybe = 1
            no = 0
        if (vote == "no"):
            yes = 0
            maybe = 0
            no = 1
        c.execute('''INSERT INTO option_votes VALUES (?,?,?,?,?)''', (option_id, user.id, yes, maybe, no))
    conn.commit()

    so = getSurveyOptions(s)
    button_list = []
    if (s[4] == 1):
        cols = 3
    else:
        cols = 2
    msgtext = surveyText(s)
    for opt in so:
        opt = getOptionVotes(opt)


        msgtext += '''*%s*: %s yes, ''' % (opt.text, opt.yes)
        if (s[4] == 1):
            msgtext += '''%s maybe, ''' % opt.maybe
        msgtext += '''%s no\n''' % opt.no

        button_list.append(
            InlineKeyboardButton("YES (%s)" % opt.getYes(), callback_data=('%s-%s-yes' % (s[0], opt.id))))
        if (s[4] == 1):
            button_list.append(
                InlineKeyboardButton("MAYBE (%s)" % opt.getMaybe(), callback_data=('%s-%s-maybe' % (s[0], opt.id))))
        button_list.append(InlineKeyboardButton("NO (%s)" % opt.getNo(), callback_data=('%s-%s-no' % (s[0], opt.id))))


    callbackQuery.edit_message_text(text=msgtext,
                                    reply_markup=InlineKeyboardMarkup(build_menu(button_list, n_cols=cols)),
                                    parse_mode=ParseMode.MARKDOWN)
    callbackQuery.answer()
    conn.close()


def offerNewSurvey(bot, update):
    update.inline_query.answer([], switch_pm_text="Create new Survey")


def handleInlineQuery(bot, update, user_data):
    inlineQuery = update.inline_query
    user = inlineQuery.from_user
    logger.info(inlineQuery)
    logger.info(user)
    surtext, sid = inlineQuery.query.split("-")
    s = getSurveyById(sid)

    if (s is None):
        logger.info("No survey found")
    else :
        if (s[1] == user.id):
            resultList = []
            msgText = surveyText(s)
            msgText += '\n\nOptions:'
            so = getSurveyOptions(s)
            button_list = []
            if (s[4] == 1):
                cols = 3
            else:
                cols = 2

            for opt in so:
                msgText += '''\n*%s*: %s yes, ''' % (opt.getText(), opt.getYes())
                if (s[4] == 1):
                    msgText += '''%s maybe, ''' % opt.getMaybe()
                msgText += '''%s no\n''' % opt.no
                button_list.append(
                    InlineKeyboardButton("YES (%s)" % opt.getYes(), callback_data=('%s-%s-yes' % (s[0], opt.id))))
                if (s[4] == 1):
                    button_list.append(
                        InlineKeyboardButton("MAYBE (%s)" % opt.getMaybe(), callback_data=('%s-%s-maybe' % (s[0], opt.id))))
                button_list.append(
                    InlineKeyboardButton("NO (%s)" % opt.getNo(), callback_data=('%s-%s-no' % (s[0], opt.id))))
            resultList.append(
                InlineQueryResultArticle("survey-%s" % (sid,), s[2],
                    InputTextMessageContent(msgText,parse_mode=ParseMode.MARKDOWN),
                    reply_markup=InlineKeyboardMarkup(build_menu(button_list, n_cols=cols))))
            inlineQuery.answer(resultList)


def displaySurveyFromInlineHandler(bot, update):
    logger.info(update)
    result = update.callback_query
    logger.info(result)


def error(bot, update, error):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, error)


def main():
    config = ConfigParser.RawConfigParser()
    config.read('config.cfg')

    survey_id = 0
    updater = Updater(config.get("credentials", "token"))

    # Create the EventHandler and pass it your bot's token.

    def stop_and_restart(updater):
        """Gracefully stop the Updater and replace the current process with a new one"""
        updater.stop()
        logger.info("Updater stopped")
        os.execl(sys.executable, os.path.abspath(__file__), *sys.argv)
        logger.info("what am I doing here?")

    def restart(bot, update):
        logger.info("Received restart request")
        update.message.reply_text('Bot is restarting...')
        threading.Thread(target=stop_and_restart(updater)).start()

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # Add conversation handler with the states GENDER, PHOTO, LOCATION and BIO
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start),
                      CommandHandler('new', new)],

        states={
            TITLE: [MessageHandler(Filters.text, title)],

            DESCRIPTION: [CommandHandler('skip', skip_description),
                          MessageHandler(Filters.text, description)],

            SETTINGS: [MessageHandler(Filters.text, settings_maybe)],

            OPTIONS: [MessageHandler(Filters.text, option),
                      CommandHandler('end', end)]
        },

        fallbacks=[CommandHandler('cancel', cancel)],
        per_user=True
    )

    def loadData():
        try:
            f = open('backup/conversations', 'rb')
            conv_handler.conversations = pickle.load(f)
            f.close()
            f = open('backup/userdata', 'rb')
            dp.user_data = pickle.load(f)
            f.close()
        #        except FileNotFoundError as e:
        #            logger.error("Data file not found")
        except:
            logger.error(sys.exc_info()[0])

    def saveData():
        while True:
            time.sleep(60)
            # Before pickling
            resolved = dict()
            for k, v in conv_handler.conversations.items():
                if isinstance(v, tuple) and len(v) is 2 and isinstance(v[1], Promise):
                    try:
                        new_state = v[1].result()  # Result of async function
                    except:
                        new_state = v[0]  # In case async function raised an error, fallback to old state
                    resolved[k] = new_state
                else:
                    resolved[k] = v
            try:
                f = open('backup/conversations', 'wb+')
                pickle.dump(resolved, f)
                f.close()
                f = open('backup/userdata', 'wb+')
                pickle.dump(dp.user_data, f)
                f.close()
            except:
                logger.error(sys.exc_info()[0])

    loadData()
    threading.Thread(target=saveData).start()
    cb_handler = CallbackQueryHandler(updateVote, pass_user_data=True)

    dp.add_handler(CommandHandler('restart', restart, filters=Filters.user(username='@cnarg')))

    dp.add_handler(InlineQueryHandler(handleInlineQuery, pattern="survey-", pass_user_data=True))
    dp.add_handler(InlineQueryHandler(offerNewSurvey, pattern="^$", pass_user_data=True))

    dp.add_handler(ChosenInlineResultHandler(displaySurveyFromInlineHandler, pass_user_data=True, pass_chat_data=True))

    dp.add_handler(cb_handler)

    dp.add_handler(conv_handler)

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
