import random
import string
import time
import json
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from flask import Flask, request
from flask_slack import Slack
from slackclient import SlackClient
import os

client_id = os.environ['SLACK_CLIENT_ID']
client_secret = os.environ['SLACK_CLIENT_SECRET']
oauth_scope = os.environ['SLACK_BOT_SCOPE']
state = ''
redirect_uri = 'https://dailystatus.herokuapp.com/finish_auth'
# redirect_uri = 'https://6a8ad775.ngrok.io/finish_auth'
# team_id = 'T86UNPR0V'
# updates_channel = 'C89EMFXUN'

team_id = 'T0DA8RT71'
updates_channel = 'C89DCTLLA'

app = Flask(__name__)

slack = Slack(app)
slack_token = os.environ['SLACK_BOT_TOKEN']
# slack_user_token = ''
# sc = SlackClient(os.environ['SLACK_BOT_OAUTH_TOKEN'])


@app.route('/begin_auth', methods=['GET'])
def pre_install():
    state = ''.join([
        random.choice(string.ascii_letters + string.digits) for n in range(32)
        ])
    return '''
        <a href='https://slack.com/oauth/authorize?scope={0}&client_id={1}&state={2}&redirect_uri={3}'>
            Add to Slack
        </a>
    '''.format(oauth_scope, client_id, state, redirect_uri)


@app.route('/finish_auth', methods=['GET', 'POST'])
def post_install():

    # Retrieve the auth code from the request params
    auth_code = request.args['code']
    # print(auth_code)

    # An empty string is a valid token for this request
    sc = SlackClient('')

    # Request the auth tokens from Slack
    auth_response = sc.api_call(
        'oauth.access',
        client_id=client_id,
        client_secret=client_secret,
        code=auth_code
    )

    # print(auth_response)

    # Save the bot token to an environmental variable or to your data store
    # for later use

    slack_user_token = auth_response['access_token']

    # os.environ['SLACK_USER_TOKEN'] = auth_response['access_token']
    # os.environ['SLACK_BOT_TOKEN'] = auth_response['bot']['bot_access_token']

    # sc = SlackClient(os.environ['SLACK_USER_TOKEN'])
    sc = SlackClient(auth_response['access_token'])

    # Don't forget to let the user know that auth has succeeded!
    return 'Auth complete!'


def get_username(user_id, sc):
    result = sc.api_call(
        'users.info',
        user=user_id
    )

    user = {
        'name': result['user']['profile']['real_name'],
        'icon': result['user']['profile']['image_48']
    }

    if result['user']['profile']['display_name']:
        user['name'] = result['user']['profile']['display_name']

    return user


def post_update(tag, channel='#general', attachments='', **kwargs):
    # with open("token.txt", 'r') as f:
    #     user_token = f.read()
    #     print(user_token)
    #     sc = SlackClient(user_token)

    # sc = SlackClient(os.environ['SLACK_USER_TOKEN']
    # sc = SlackClient(slack_user_token)
    sc = SlackClient(os.environ['SLACK_BOT_OAUTH_TOKEN'])
    user = get_username(kwargs.get('user_id'), sc)
    return sc.api_call(
        'chat.postMessage',
        as_user='false',
        username=user['name'],
        icon_url=user['icon'],
        channel=channel,
        link_names='true',
        text='*%s:* %s' % (tag, kwargs.get('text')),
        attachments=attachments
    )


@slack.command('get status', token=slack_token,
               team_id=team_id, methods=['POST'])
def get_status(**kwargs):
    sc = SlackClient(os.environ['SLACK_BOT_OAUTH_TOKEN'])
    latest = datetime.now().timestamp()
    while True:
        result = sc.api_call(
            'channels.history',
            channel=updates_channel,
            oldest=(datetime.now() - timedelta(days=14)).timestamp(),
            latest=latest
            # count=1
        )
        result = dict(result)
        if result['ok']:
            for message in list(result['messages']):
                # print(message)
                if 'username' in dict(message) and dict(message)['username'] == get_username(kwargs.get('user_id'), sc)['name']:
                    return message
                latest = dict(message)['ts']
            # return slack.response(result['messages'][3]['text'])
            # return result['messages']
        else:
            return result['error']
        if not result['has_more']:
            return None



@slack.command('goodbye', token=slack_token,
               team_id=team_id, methods=['POST'])
def goodbye(**kwargs):
    update = dict(post_update('goodbye', **kwargs))
    response = 'Successfully posted your message to <#%s>.' % update['channel']
    return slack.response(response)


@slack.command('standup', token=slack_token,
               team_id=team_id, methods=['POST'])
def standup(**kwargs):
    tag = ':arrow_double_up: Standup'
    last_status = get_status(**kwargs)
    if last_status and '*%s:* %s' % (tag, kwargs.get('text')) == last_status['text']:
        return slack.response('That status is already posted')

    update = dict(post_update(tag, updates_channel, **kwargs))

    if update['ok']:
        response = 'Successfully posted your message to <#%s>.' % update['channel']
    else:
        response = update['error']
        # response = os.environ['SLACK_USER_TOKEN']
        # response = ':frowning: Sorry, something went wrong trying to post your standup'
    return slack.response(response)
    # sc = SlackClient(os.environ['SLACK_USER_TOKEN'])
    # return sc.api_call(
    #     'users.identity'
    # )


@slack.command('sitdown', token=slack_token,
               team_id=team_id, methods=['POST'])
def sitdown(**kwargs):
    last_status = get_status(**kwargs)
    attachments = ''
    tag = ':arrow_double_down: Sitdown'

    if last_status and ':arrow_double_up: Standup' in last_status['text']:
        attachments = [{
            'text': last_status['text'],
            'mrkdwn_in': ['text']
        }]
    else:
        tag = ':arrow_double_up: Standup ' + tag

    update = dict(post_update(tag, updates_channel, attachments, **kwargs))
    if update['ok']:
        response = 'Successfully posted your message to <#%s>.' % update['channel']
    else:
        response = ':frowning: Sorry, something went wrong trying to post your sitdown'
    return slack.response(response)

app.add_url_rule('/goodbye', view_func=slack.dispatch)
app.add_url_rule('/standup', view_func=slack.dispatch)
app.add_url_rule('/sitdown', view_func=slack.dispatch)


# @app.route('/hello', methods=['POST'])
# def hello():
#     return 'Hello Slack!'

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
    # print(get_status(user_name='joshuarrrr'))
    # print(get_username('U89D1FH1A'))
    # print(get_username('U86QEU8GJ'))
