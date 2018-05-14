import sqlite3


def main():
    conn = sqlite3.connect('meetbot.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (user_id numeric, username text, first_name text, name text)''')
    c.execute(
        '''CREATE TABLE IF NOT EXISTS surveys (user_id numeric, title text, description text, setting_maybe numeric)''')
    c.execute('''CREATE TABLE IF NOT EXISTS survey_options (survey_id numberic, option text)''')
    c.execute('''CREATE TABLE IF NOT EXISTS option_votes (option_id numberic, user_id numeric,
        yes numeric, maybe numeric, no numeric)''')
    conn.commit()



if __name__ == '__main__':
    main()
