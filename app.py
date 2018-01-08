import random
import string

from flask import Flask, request
from flask_slack import Slack
from slackclient import SlackClient
import os

client_id = os.environ['SLACK_CLIENT_ID']
client_secret = os.environ['SLACK_CLIENT_SECRET']
oauth_scope = os.environ['SLACK_BOT_SCOPE']
state = ''
redirect_uri = 'https://dailystatus.herokuapp.com/finish_auth'

app = Flask(__name__)

slack = Slack(app)
slack_token = os.environ['SLACK_BOT_TOKEN']
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
    with open("token.txt", 'w') as f:
        f.write(auth_response['access_token'])

    # os.environ['SLACK_USER_TOKEN'] = auth_response['access_token']
    # os.environ['SLACK_BOT_TOKEN'] = auth_response['bot']['bot_access_token']

    # sc = SlackClient(os.environ['SLACK_USER_TOKEN'])
    sc = SlackClient(auth_response['access_token'])

    # Don't forget to let the user know that auth has succeeded!
    return 'Auth complete!'


def postUpdate(tag, channel='#general', **kwargs):
    with open("token.txt", 'w') as f:
        user_token = f.read()

    # sc = SlackClient(os.environ['SLACK_USER_TOKEN']
    sc = SlackClient(user_token)
    return sc.api_call(
        'chat.postMessage',
        as_user='false',
        username=kwargs.get('user_name'),
        channel=channel,
        link_names='true',
        text='*%s:* %s' % (tag, kwargs.get('text'))
    )


@slack.command('goodbye', token=slack_token,
               team_id='T86UNPR0V', methods=['POST'])
def goodbye(**kwargs):
    update = dict(postUpdate('goodbye', **kwargs))
    response = 'Successfully posted your message to <#%s>.' % update['channel']
    return slack.response(response)


@slack.command('standup', token=slack_token,
               team_id='T86UNPR0V', methods=['POST'])
def standup(**kwargs):
    update = dict(postUpdate(':arrow_double_up: Standup', '#standups', **kwargs))
    if update['ok']:
        response = 'Successfully posted your message to <#%s>.' % update['channel']
    else:
        response = update
        # response = os.environ['SLACK_USER_TOKEN']
        # response = ':frowning: Sorry, something went wrong trying to post your standup'
    # return slack.response(response)
    # sc = SlackClient(os.environ['SLACK_USER_TOKEN'])
    return sc.api_call(
        'users.identity'
    )


@slack.command('sitdown', token=slack_token,
               team_id='T86UNPR0V', methods=['POST'])
def sitdown(**kwargs):
    update = dict(postUpdate(':arrow_double_down: Sitdown', '#standups', **kwargs))
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
