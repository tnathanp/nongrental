import os
import pymongo
import math
from datetime import datetime, timedelta
from flask import Flask, request, abort
from linebot import (LineBotApi, WebhookHandler)
from linebot.exceptions import (InvalidSignatureError)
from linebot.models import *

app = Flask(__name__)

# line integration
line_bot_api = LineBotApi('BfHsLJLLPyIDbz8GQIjsMt0cgcMNpllkhR3Sk3zNSrF9ChcsBfLobLOYWYdynu2VngMJZ2p/Fit6QI7QuA4x4EaBxptmrWpcceTpHKahGiTGObo7wNngbMzC3XsSq9PqjHAD3qEBI+xIAaGGZQge4AdB04t89/1O/w1cDnyilFU=')
handler = WebhookHandler('0d6d251da9eb5f1a0c7f8057999f10d5')
# database integration
client = pymongo.MongoClient("mongodb+srv://dogproject:8tnUqZwq1tClK0ya@cluster-83va3.mongodb.net/")
db = client.dog
# getting dog list ready
retrieved = db.list.find()
doglist = []
length = db.list.find().count()
for i in range(length):
    doglist.append(CarouselColumn(
        thumbnail_image_url=retrieved[i]['Image'],
        title=retrieved[i]['Name'],
        text='Breed: '+str(retrieved[i]['Breed'])+'\nRate: '+str(retrieved[i]['Price'])+' Baht/hour',
        actions=[
            PostbackAction(
                label='Rent',
                display_text=retrieved[i]['Name'],
                data='action=picktime&itemid='+str(i+1)
            ),
            URIAction(
                label='View picture',
                uri=retrieved[i]['Image']
            )
        ]
    )
    )

# global variable declaration
user_location = ''

# function to extract parameter
def dataToDict(s):
    ans = dict()
    if '&' not in s:
        ans[s.split('=')[0]] = s.split('=')[1]
        return ans
    else:
        t = s.split('&')
        for i in range(s.count('&')+1):
            ans[t[i].split('=')[0]] = t[i].split('=')[1]
        return ans

# function to calculate time
def convertToDuration(a, b):
    start = datetime.strptime(a, "%Y-%m-%dT%H:%M")
    end = datetime.strptime(b, "%Y-%m-%dT%H:%M")
    diff = end-start
    dhour = int(diff.total_seconds()/3600)
    dmin = (diff.total_seconds()/60) % 60
    return {'hour': int(dhour), 'minute': int(dmin)}

def calculateTime(t):
    cur = datetime.strptime(t, "%Y-%m-%dT%H:%M")
    cur = cur + timedelta(seconds=1800)
    return cur.strftime("%Y-%m-%dT%H:%M")

# start of the API
@app.route("/")
def check():
    return 'API is running..'


@app.route("/testdb")
def testdb():
    info = db.list.find()
    res = ''
    for i in range(6):
        res += str(info[i]['Name'])
    return res


@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)
    return 'OK'


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    if event.message.text.lower() == 'rent a dog':
        line_bot_api.reply_message(event.reply_token, [
            TextSendMessage(text='Could you tell me where do you live? ☺️',
                            quick_reply=QuickReply(items=[QuickReplyButton(action=LocationAction(label="Choose location"))])
                            )
        ])


@handler.add(MessageEvent, message=LocationMessage)
def handle_location(event):
    list_reply = TemplateSendMessage(
        alt_text='List 🐶',
        template=CarouselTemplate(
            columns=doglist
        )
    )
    global user_location
    user_location = str(event.message.address)
    line_bot_api.reply_message(event.reply_token, [TextSendMessage(text="How about choosing your bestfriend? 🐶"), list_reply])


@handler.add(PostbackEvent)
def handle_postback(event):
    param = dataToDict(event.postback.data)
    if param['action'] == 'picktime':
        date_picker = TemplateSendMessage(
            alt_text='Pick start time for your dog~!',
            template=ButtonsTemplate(
                text='We will arrive with a cutie dog at this time',
                thumbnail_image_url='https://i.ibb.co/LN7T4Fv/starttime.jpg',
                title='Start time',
                actions=[
                    DatetimePickerTemplateAction(
                        label='Choose',
                        data='action=picktime2&itemid='+str(param['itemid']),
                        mode='datetime',
                        initial=datetime.now().strftime("%Y-%m-%d")+'T08:00',
                        min=datetime.now().strftime("%Y-%m-%d")+'T08:00',
                        max='2021-01-01T12:00'
                    )
                ]
            )
        )
        line_bot_api.reply_message(event.reply_token, date_picker)
    elif param['action'] == 'picktime2':
        date_picker = TemplateSendMessage(
            alt_text='Pick end time for your dog~!',
            template=ButtonsTemplate(
                text='You have to say goodbye to your dog at this time 🥺',
                thumbnail_image_url='https://i.ibb.co/MfsTQKT/endtime.jpg',
                title='End time',
                actions=[
                    DatetimePickerTemplateAction(
                        label='Choose',
                        data='action=payment&itemid='+str(param['itemid'])+'&starttime='+str(event.postback.params['datetime']),
                        mode='datetime',
                        initial=calculateTime(event.postback.params['datetime']),
                        min=calculateTime(event.postback.params['datetime']),
                        max='2021-01-01T12:00'
                    )
                ]
            )
        )
        line_bot_api.reply_message(event.reply_token, date_picker)
    elif param['action'] == 'payment':
        param['endtime'] = str(event.postback.params['datetime'])
        duration = convertToDuration(param['starttime'], param['endtime'])
        flex_message = FlexSendMessage(
            alt_text='Confirmation',
            contents={
                'type': 'bubble',
                'direction': 'ltr',
                'hero': {
                    'type': 'image',
                    'url': retrieved[int(param['itemid'])-1]['Image'],
                    'size': 'full',
                    'aspectRatio': '20:13',
                    'aspectMode': 'cover'
                },
                'body': {
                    'type': 'box',
                    'layout': 'vertical',
                    'spacing': 'md',
                    'contents': [
                        {
                            'type': 'text',
                            'text': retrieved[int(param['itemid'])-1]['Name'],
                            'size': 'xl',
                            'weight': 'bold'
                        },
                        {
                            'type': 'box',
                            'layout': 'horizontal',
                            'contents': [
                                {
                                    'type': 'text',
                                    'text': 'Breed',
                                    'color': '#aaaaaa',
                                    'flex': 2
                                },
                                {
                                    'type': 'text',
                                    'text': retrieved[int(param['itemid'])-1]['Breed'],
                                    'flex': 4,
                                    'wrap': True
                                }
                            ]
                        },
                        {
                            'type': 'box',
                            'layout': 'horizontal',
                            'contents': [
                                {
                                    'type': 'text',
                                    'text': 'Sex',
                                    'color': '#aaaaaa',
                                    'flex': 2
                                },
                                {
                                    'type': 'text',
                                    'text': retrieved[int(param['itemid'])-1]['Sex'],
                                    'flex': 4,
                                    'wrap': True
                                }
                            ]
                        },
                        {
                            'type': 'box',
                            'layout': 'horizontal',
                            'contents': [
                                {
                                    'type': 'text',
                                    'text': 'Age',
                                    'color': '#aaaaaa',
                                    'flex': 2
                                },
                                {
                                    'type': 'text',
                                    'text': retrieved[int(param['itemid'])-1]['Age'],
                                    'flex': 4,
                                    'wrap': True
                                }
                            ]
                        },
                        {
                            'type': 'box',
                            'layout': 'horizontal',
                            'contents': [
                                {
                                    'type': 'text',
                                    'text': 'Size',
                                    'color': '#aaaaaa',
                                    'flex': 2
                                },
                                {
                                    'type': 'text',
                                    'text': retrieved[int(param['itemid'])-1]['Size'],
                                    'flex': 4,
                                    'wrap': True
                                }
                            ]
                        },
                        {
                            'type': 'box',
                            'layout': 'horizontal',
                            'contents': [
                                {
                                    'type': 'text',
                                    'text': 'Traits',
                                    'color': '#aaaaaa',
                                    'flex': 2
                                },
                                {
                                    'type': 'text',
                                    'text': retrieved[int(param['itemid'])-1]['Traits'],
                                    'flex': 4,
                                    'wrap': True
                                }
                            ]
                        },
                        {
                            'type': 'box',
                            'layout': 'horizontal',
                            'contents': [
                                {
                                    'type': 'text',
                                    'text': 'Caution',
                                    'color': '#aaaaaa',
                                    'flex': 2
                                },
                                {
                                    'type': 'text',
                                    'text': retrieved[int(param['itemid'])-1]['Caution'],
                                    'flex': 4,
                                    'wrap': True
                                }
                            ]
                        },
                        {
                            'type': 'box',
                            'layout': 'horizontal',
                            'contents': [
                                {
                                    'type': 'text',
                                    'text': 'Location',
                                    'color': '#aaaaaa',
                                    'flex': 2
                                },
                                {
                                    'type': 'text',
                                    'text': str(user_location),
                                    'style': 'italic',
                                    'color': '#666666',
                                    'flex': 4,
                                    'wrap': True
                                }
                            ]
                        },
                        {
                            'type': 'box',
                            'layout': 'horizontal',
                            'contents': [
                                {
                                    'type': 'text',
                                    'text': 'Start Time',
                                    'color': '#aaaaaa',
                                    'flex': 2
                                },
                                {
                                    'type': 'text',
                                    'text': param['starttime'].split('T')[1]+' '+param['starttime'].split('T')[0],
                                    'weight': 'bold',
                                    'flex': 4
                                }
                            ]
                        },
                        {
                            'type': 'box',
                            'layout': 'horizontal',
                            'contents': [
                                {
                                    'type': 'text',
                                    'text': 'End Time',
                                    'color': '#aaaaaa',
                                    'flex': 2
                                },
                                {
                                    'type': 'text',
                                    'text': param['endtime'].split('T')[1]+' '+param['endtime'].split('T')[0],
                                    'weight': 'bold',
                                    'flex': 4
                                }
                            ]
                        }
                    ]
                },
                'footer': {
                    'type': 'box',
                    'layout': 'vertical',
                    'contents': [
                        {
                            'type': 'button',
                            'style': 'primary',
                            'color': '#905c44',
                            'action': {
                                'type': 'uri',
                                'label': 'Confirm and Pay ฿'+str(math.ceil((duration['hour'] * int(retrieved[int(param['itemid'])-1]['Price'])) + (duration['minute'] * (float(retrieved[int(param['itemid'])-1]['Price'])))/60)),
                                'uri': 'http://example.com'
                            }
                        }
                    ]
                }
            }
        )
        line_bot_api.reply_message(event.reply_token, flex_message)


if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
