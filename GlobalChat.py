import datetime
import easygui
import flet as ft
import pyrebase
import pybase64
from googletrans import Translator
import sys
import os

config = {
  "apiKey": "AIzaSyCfyTwW8jVGafxCfARQsDRMIvaRMISQfk0",
  "authDomain": "chatapp-d1767.firebaseapp.com",
  "databaseURL": "https://chatapp-d1767-default-rtdb.asia-southeast1.firebasedatabase.app",
  "projectId": "chatapp-d1767",
  "storageBucket": "chatapp-d1767.appspot.com",
  "messagingSenderId": "544717018040",
  "appId": "1:544717018040:web:3f4cb15a92e10eef10754d",
  "measurementId": "G-YPF6SC5WLV"
}

firebase = pyrebase.initialize_app(config)
database = firebase.database()
from googletrans.constants import LANGUAGES
languages = dict( zip( LANGUAGES.values(), LANGUAGES.keys() ) )

def translate(text, page):
    
    if page.client_storage.get("translating"):
        language = page.client_storage.get("language")

        if type(text) == list:
            translations = list()
            for i in text:
                translated_text = page.client_storage.get(language + i)
                if translated_text:
                    pass
                else:
                    translated_text = Translator().translate(i, dest = language).text
                    page.client_storage.set(language + i, translated_text)
                translations.append(translated_text)
            return translations
        
        translated_text = page.client_storage.get(language + text)
        
        if translated_text != None:
            return translated_text
        
        translated_text =  Translator().translate(text, dest = language).text
        page.client_storage.set(language + text,translated_text)
        return translated_text
    
    return text

class Message():
    def __init__(self, page, user: str, text: str, message_type:str, time_stamp: str):
        self.user = user
        self.text = text if message_type.startswith("image") else translate(text, page)
        self.message_type = message_type
        self.time_stamp = time_stamp

class TranslatedMessage():
    def __init__(self, page, user: str, text: str, message_type:str, time_stamp: str):
        self.page = page
        self.user = user
        self.text = text
        self.message_type = message_type
        self.time_stamp = time_stamp

class ChatMesage(ft.Row):
    
    def __init__(self, message: Message):
        length = len(message.text)
        text = message.text
        super().__init__()
        max_length = 188
        if length > max_length:
            new_text = ''
            for i in range(1, length // max_length + 1 ):
                index = text[: max_length * i].rfind(" ")
                if index == -1:
                    index = max_length
                if text[max_length * (i-1): max_length * i].count("\n") > 0:
                    continue
                new_text = text[:index].strip() + "\n" + text[index:].strip()
                text = new_text
        
        self.vertical_alignment = "start"
        self.controls = [
            ft.CircleAvatar(
                content = ft.Text( message.user[:1].capitalize()  ),
                color = ft.colors.WHITE,
                bgcolor = self.get_avatar_color( message.user ),
                ),
                ft.Column(
                    [
                     ft.Row([ft.Text(message.user,
                                     weight = "bold",
                                     color = self.get_avatar_color( message.user ),
                                     ),
                             ft.Text(message.time_stamp,
                                     style = ft.TextThemeStyle.BODY_SMALL,
                                     color = ft.colors.GREY_700),
                             ],
                           ),
                     ft.Text(text,
                             selectable=True),
                    ], 
                    tight=True,
                    spacing=5,
                ),
            ]
        
    def get_avatar_color(self, name):
        colors_lookup = [
            ft.colors.AMBER,
            ft.colors.BLUE,
            ft.colors.BROWN,
            ft.colors.CYAN,
            ft.colors.GREEN,
            ft.colors.INDIGO,
            ft.colors.LIME,
            ft.colors.ORANGE,
            ft.colors.PINK,
            ft.colors.PURPLE,
            ft.colors.RED,
            ft.colors.TEAL,
            ft.colors.YELLOW,
        ]
        return colors_lookup[hash(name) % len(colors_lookup)]


class Channel:
    def __init__(self, page, name = "Global Chat", user = "unknown"):
        self.name = name
        self.page = page
        self.user = user

    def get_time(self):
        time = datetime.datetime.now().strftime("%D %H:%M")
        return time [3:5] + '/' + time[0:2] + time[5:]

    def send_message(self, text, type):
        self.page.pubsub.send_all( Message( self.page,
                                            user = self.user,
                                            text = text,
                                            message_type = type,
                                            time_stamp = self.get_time(),
                                            )
        )

    def login(self, user, first_time = False):
        self.page.session.set("username", user)
        self.page.session.set("logged in", True)
        self.page.client_storage.set("username", user)
        database.child("Global Chat").push({"login_message": (user, self.get_time())})
        login_text = f"{user} has joined" + " for the first time" * first_time
        self.page.pubsub.send_all( Message( self.page,
                                            user = 'System',
                                            text = login_text,
                                            message_type = "login_message",
                                            time_stamp = self.get_time()
                                            )
                                 ) 
        translate_text = """You can use the Translator to select a language.\n\
Then all the text will be translated to the chosen language."""
        
        self.page.dialog = ft.AlertDialog(open = True,
                                     modal = False,
                                     shape = ft.RoundedRectangleBorder( radius = 10 ),
                                     title = ft.Text(translate("Welcome", self.page)),
                                    
                                     content = ft.Text( translate(f"Welcome {user}, please be respectful to everyone.\n" + translate_text, self.page) ),
                                        )
        self.user = user
        
    def create_account(self, user, password, email):
        database.child("users_passwords").child(user).set({"password":password, "email" : email})
        self.login(user, first_time = True)
    
    def upload_image(self, image_base64_encoded, image_type):
        database.child(self.name).push({self.user + "_image_base64_encoded": (image_base64_encoded, self.get_time(), image_type)})
        self.send_message(image_base64_encoded, "image_" + image_type)

    def upload_text(self, text):
        database.child(self.name).push({self.user:(text, self.get_time())})
        self.send_message(text, "chat_message")

class Image(ft.Row):
    def __init__(self, message: Message):
        super().__init__()
        self.user = message.user
        self.text = message.text
        self.message_type = message.message_type
        self.time_stamp = message.time_stamp
        self.vertical_alignment = "start"

        avatar = ft.CircleAvatar(
                content = ft.Text( self.user[:1].capitalize() ),
                color = ft.colors.WHITE,
                bgcolor = self.get_avatar_color( self.user ),
                )
        heading = ft.Row([ft.Text(self.user,
                                  weight="bold",
                                  color = self.get_avatar_color( self.user ),
                                ),
                         ft.Text(self.time_stamp,
                                 style = ft.TextThemeStyle.BODY_SMALL,
                                 color = ft.colors.GREY_700),
                         ft.TextButton( "See original", on_click = self.rerender_image, data = "Modified" )
                         ],
                        )
        width = height = None
        if self.message_type.endswith("Image"):
            width = 600
            height = 500
        else:
            heading.controls = heading.controls[:2]

        image = ft.Image(src_base64 = self.text,
                          width = width,
                          height = height,
                          fit = ft.ImageFit.CONTAIN)
        self.controls = [avatar,
                         ft.Column( [heading,
                                     image,
                                    ],
                                    tight=True,
                                    spacing=5,
                                  ),
                        ]
            
    def rerender_image(self, e):
        image = self.controls[1].controls[1]
        text_button = self.controls[1].controls[0].controls[2]
        if text_button.data == "Original":
            image.width = 600
            image.height = 500
            text_button.text = "See original"
            text_button.data = "Modified"

        else:
            image.width = None
            image.height = None
            text_button.text = "See modified"
            text_button.data = "Original"
        self.page.update()

    def get_avatar_color(self, name):
        colors_lookup = [
            ft.colors.AMBER,
            ft.colors.BLUE,
            ft.colors.BROWN,
            ft.colors.CYAN,
            ft.colors.GREEN,
            ft.colors.INDIGO,
            ft.colors.LIME,
            ft.colors.ORANGE,
            ft.colors.PINK,
            ft.colors.PURPLE,
            ft.colors.RED,
            ft.colors.TEAL,
            ft.colors.YELLOW,
        ]
        return colors_lookup[hash(name) % len(colors_lookup)]

def main(page: ft.Page):

    def s_translate(text):
        translation = translate(text, page)
        return translation
    
    page.session.set("logged in", False)
    channel = Channel(page = page)
    page.horizontal_alignment = "stretch"
    page.title = s_translate('Chat')

    page.theme = ft.Theme(
        color_scheme = ft.ColorScheme(
            primary = ft.colors.PURPLE,
            primary_container = ft.colors.BLACK),
        )

    def restart():
        os.execv(sys.executable, ['python'] + sys.argv)

    def shortcut_open_translator():
        translate_iconbutton.data = not translate_iconbutton.data
        if translate_iconbutton.data:
            page.dialog = translator
            translator.on_dismiss = open_translator
        else:
            translator.on_dismiss = None
        page.dialog.open = translate_iconbutton.data
        page.update()

    def open_translator(e):
        shortcut_open_translator()

    def reset_translator(e):
        if page.client_storage.get("translating"):
            page.client_storage.set("translating", False)   
            page.window_destroy()
            restart()
        else:
            language_dropdown.error_text = "The Translator is not running"
            page.snack_bar = ft.SnackBar( content = ft.Text("The Translator is not running", color = ft.colors.WHITE),
                                         bgcolor = ft.colors.RED_700,
                                         behavior = ft.SnackBarBehavior.FLOATING,
                                          open = True)
        page.update()

    def start_translating(e):
        if language_dropdown.value:
            
            page.dialog = translator
            translate_iconbutton.data = not translate_iconbutton.data
            page.dialog.open = translate_iconbutton.data
            page.client_storage.set("translating", True)
            page.client_storage.set("language", languages[language_dropdown.value])
            page.window_destroy()
            restart()
        else:
            language_dropdown.error_text = "Please choose a language first"
            page.snack_bar = page.snack_bar = ft.SnackBar(ft.Text(s_translate("Please choose a language first"), color = ft.colors.WHITE),
                                                          bgcolor = ft.colors.RED_700,
                                                          duration = 2500,
                                                          behavior = ft.SnackBarBehavior.FLOATING,
                                                          open = True,
                                                          )
        page.update()

    translate_iconbutton = ft.IconButton(icon = ft.icons.LANGUAGE,
                                         on_click = open_translator,
                                         tooltip = s_translate("Open the translator") + "(ctrl shift t)",
                                         data = False) 
    translate_button = ft.TextButton(text = s_translate("Translate"), on_click = start_translating)
    cancel_button = ft.TextButton(text = s_translate("Cancel"), on_click = open_translator)
    language_dropdown = ft.Dropdown(hint_text = s_translate("Translation"),
                                    width=None,
                                    options=[ft.dropdown.Option(i) for i in languages.keys()],
                                    )
    translator_on_button = ft.IconButton(icon = ft.icons.STOP,
                                         tooltip = s_translate("Reset the translator"),
                                         on_click = reset_translator)
    translator = ft.AlertDialog(modal = False,
                                title = ft.Text(s_translate("The Translator")),
                                shape = ft.RoundedRectangleBorder( radius = 2 ),
                                content = ft.Column(controls = [ft.Text(s_translate("The Translator will be slow"),
                                                                        color = ft.colors.RED),
                                                                language_dropdown],
                                                    width = 400,
                                                    height = 90,
                                                    alignment = ft.MainAxisAlignment.CENTER),
                                actions = [ ft.Row( [ translator_on_button , ft.Row( [cancel_button, translate_button] ) ],
                                                    alignment = ft.MainAxisAlignment.SPACE_BETWEEN ) 
                                          ],
                                on_dismiss = open_translator,
                                open = True)
            
    def change_all_topics():
        page.dialog = all_topics
        page.dialog.open = topics.data = not topics.data
        page.update()

    def change_channel(label):
        page.drawer.open = False
    
        if label == "Feedback":
            channel.name = label
        else:
            channel.name = channel_names[trans_channel_names.index(label)]
            change_all_topics()
        if page.session.get("channel") != label:
            
            page.appbar.title.value = label
            channel_name.content.value = label
            page.session.set("channel", channel.name)
            unload_messages()
            load_messages()
            new_message.focus()
            page.update()
        
    def logout_user():
        if chat_container in page.controls:
            page.controls.remove(chat_container)
            page.controls.remove(message_sender)
            page.dialog = login_dialog
            page.dialog.open = True
            page.client_storage.set("stay logged in", False)
            page.session.set("logged in", False)
        page.drawer.open = False
        page.update()

    channel_names = ["Global Chat", "Cooking", "Gaming", "Sports", "Studies",
                     "Music", "Technology", "Fitness", "Fashion", "Programming"]
    trans_channel_names = [ s_translate(channel_name) for channel_name in channel_names]
        
    logout = ft.TextButton(
                content = ft.Text(s_translate("Log-out"), size = 20, color = ft.colors.WHITE),
                on_click = lambda x: logout_user()
            )
    feedback = ft.TextButton(
                content = ft.Text(s_translate("Give feedback"), size = 20, color = ft.colors.WHITE),
                on_click = lambda x: change_channel("Feedback")
                )
    half_topics1 = [ft.Text("—"*18)]
    half_topics2 = [ft.Text("—"*18)]

    def create_text_button(text):
        return ft.TextButton(content = ft.Text(text, size = 30), on_click = lambda x: change_channel(text))
    
    for i in range(len(channel_names)):
        name = trans_channel_names[i]
        item = [create_text_button(name), ft.Text("—"*18)]
        if i % 2 == 0:
            half_topics1.extend(item)
        else:
            half_topics2.extend(item)

    def close_all_topics(e):
        page.dialog = all_topics
        page.dialog.open = topics.data = False
        page.update()

    def open_all_topics(e):
        page.dialog = all_topics
        page.dialog.open = topics.data = True
        page.update()

    topics = ft.TextButton( content = ft.Text(s_translate("Topics"),
                                              size = 20, color = ft.colors.WHITE),
                                              on_click = open_all_topics,
                                              data = False)
                                              
    all_topics = ft.AlertDialog(modal = False,
               title = ft.Text(s_translate("Topics"), size = 25),
               shape = ft.RoundedRectangleBorder( radius = 2 ),
               on_dismiss = close_all_topics,
               content = ft.Row(controls = [ft.Column(half_topics1, spacing = 3),
                                            ft.VerticalDivider(),
                                            ft.Column(half_topics2, spacing= 3)]),
               open = True)
    
    page.drawer = ft.NavigationDrawer(controls=[],
                                      surface_tint_color = ft.colors.PURPLE_100,
                                      shadow_color = ft.colors.PURPLE_200,
                                      )
    channel_name = ft.TextButton( content = ft.Text(s_translate("Global Chat"), size = 25, color = ft.colors.WHITE),
                                  disabled = True)
    page.drawer.controls.extend([ ft.Divider(), channel_name, ft.Divider(), topics, feedback, logout])
    
    page.session.set("channel", s_translate("Global Chat"))

    def theme_change(e):
        shortcut_theme_change()

    def shortcut_theme_change():

        if page.theme_mode == ft.ThemeMode.LIGHT:
            page.theme_mode = ft.ThemeMode.DARK
            page.appbar.bgcolor = ft.colors.BLACK87
            theme_swich.icon = ft.icons.DARK_MODE_OUTLINED
            theme_swich.tooltip = s_translate("Switch to light mode") + "\n (ctrl t)"
            page.client_storage.set("dark theme", True)
            
        else: 
            page.theme_mode = ft.ThemeMode.LIGHT
            page.appbar.bgcolor = ft.colors.GREY_300
            theme_swich.icon = ft.icons.LIGHT_MODE_OUTLINED
            theme_swich.tooltip = s_translate("Switch to dark mode") + "\n (ctrl t)"
            page.client_storage.set("dark theme", False)

        
        page.update()    

    def upload_image(e):
        shortcut_upload_image()

    def shortcut_upload_image():
        if channel.name == "Feedback":
           page.snack_bar = ft.SnackBar(ft.Text(s_translate("Unfortunatly you cannot send an image or a gif in this channel"), color = ft.colors.WHITE),
                                        bgcolor = ft.colors.BLUE,
                                        duration = 2500,
                                        behavior = ft.SnackBarBehavior.FLOATING,
                                        open = True,
                                        )
        else:
            image_directory = easygui.fileopenbox()
            if image_directory == None:
                return None
            image_type = "Image"
            for extention in appropriate_image_extentions:
                if image_directory.endswith(extention):
 
                    with open(image_directory, "rb") as img_file:
                        image_base64_encoded = pybase64.b64encode(img_file.read()).decode('utf-8')
                    if image_directory.endswith(".gif"):
                       image_type = "Gif"
                    channel.upload_image(image_base64_encoded, image_type)
                    break
            else:
                page.snack_bar = ft.SnackBar(ft.Text(s_translate("Enter a valid image or gif"), color = ft.colors.WHITE),
                                             bgcolor = ft.colors.RED_700,
                                             duration = 2500,
                                             behavior = ft.SnackBarBehavior.FLOATING,
                                             open = True,
                                             )
        page.update()       

    def show_drawer(e):
        page.drawer.open = True
        page.drawer.update()

    theme_swich = ft.IconButton(icon = ft.icons.DARK_MODE_OUTLINED,
                                 on_click = theme_change,
                                 tooltip = s_translate("Switch to light mode") + "\n (ctrl t)"
                                 )
    upload_image_button = ft.IconButton(icon = ft.icons.ADD_PHOTO_ALTERNATE,
                          on_click = upload_image,
                          tooltip = s_translate("Upload images or gifs") + "\n (ctrl i)"
                         )

    def send_clicked(e):
        if page.drawer.open == True:
            return None
        if new_message.value != len(new_message.value) * '\n':
            text_message = new_message.value.strip(' \n')
            new_message.value =""
            channel.upload_text(text = text_message)
        page.update()


    def open_login(e):
        page.dialog = login_dialog
        page.dialog.open = True
        page.update()

    def open_create_account(e):

        page.dialog = ft.AlertDialog(open = True,
                                     modal = True,
                                     title = ft.Text(f"{s_translate('Create account')} {' ' * 68}"),
                                     content = ft.Column( [ ft.Row( [ create_username, create_email ],),
                                                            ft.Row( [  create_password, confirm_create_password], ),
                                                            auto_login_checkbox,
                                                          ], tight = True ),
                                     actions = [ ft.Row( [ ft.TextButton(s_translate("Log-in"), on_click =  open_login),
                                                          ft.TextButton(s_translate("Create"), on_click =  create_account), 
                                                          ],
                                                          alignment = ft.MainAxisAlignment.SPACE_BETWEEN,
                                                       ),
                                               ],
                                     inset_padding = ft.padding.symmetric(horizontal = 180),
                                     actions_alignment = ft.MainAxisAlignment.END,
                                     )
        page.update()
    
    def login_user():
       unload_messages()
       load_messages()
       login_password.value = None
       channel.login(user = page.client_storage.get("username"))
       page.add(chat_container, message_sender)
       page.update()

    def login(e):      

        user = login_username.value
        password = login_password.value

        users = database.child("users_passwords").get().val()
        if users: # To check if there are any users other wise .keys() would raise error
            users = users.keys()
            if user in users:
                stored_password = database.child("users_passwords").child(user).get().val()['password']

        login_username.error_text = None
        login_password.error_text = None


        if not users or user not in users:
            login_username.error_text = s_translate("Username does not exist")
            login_username.focus()

        elif stored_password != password:
            login_password.error_text = s_translate("Wrong password")
            login_password.focus()

        else:
            unload_messages()
            load_messages()
            page.client_storage.set("stay logged in", auto_login_checkbox.value)
            login_password.value = None
            channel.login(user = user)
            page.add(chat_container, message_sender)
            page.update()

        page.dialog.update()  

    def create_account(e):

        users = database.child("users_passwords").get().val()
        if users: # To check if there are any users
            users = database.child("users_passwords").get().val().keys()

        user = create_username.value
        email = create_email.value
        password = create_password.value
        confirm_password = confirm_create_password.value

        create_username.error_text = None
        create_email.error_text = None
        confirm_create_password.error_text = None
        create_password.error_text = None

        if user == '':
            create_username.error_text = s_translate("Username cannot be empty")
            create_username.focus()

        elif user.startswith(' '):
            create_username.error_text = s_translate("Username cannot begin\n with a space")
            create_username.focus()
            

        elif users and user in users:
            create_username.error_text = s_translate("Username already exists")
            create_username.focus()
            

        elif len(user) > 20:
            create_username.error_text = s_translate("Username is too long")
            create_username.focus()
            

        elif password == '':
            create_password.error_text = s_translate("Password cannot be empty")
            create_password.focus()
            
        elif len(password) < 6:
            create_password.error_text = s_translate("Password must be atleast\n 6 characters long")
            create_password.focus()
            

        elif confirm_password != password:
            create_password.error_text = s_translate("Passwords dont match")
            confirm_create_password.error_text = s_translate("Passwords dont match")
            create_password.focus()
            

        elif email == '':
            create_email.error_text =( "E-mail cannot be empty")
            create_email.focus()
            
        elif '@' not in email or '.' not in email:
            create_email.error_text = s_translate("Invalid E-mail")
            create_email.focus()
            

        else:
            page.dialog.open = False
            load_messages()
            page.client_storage.set("stay logged in", auto_login_checkbox.value)
            channel.create_account( user = user, password = password, email = email)

            create_username.value = None
            create_email.value = None
            create_password.value = None
            confirm_create_password.value = None

            page.add(chat_container, message_sender)
            page.update()

        page.dialog.update()

    def onMessage(message: Message):
        if message.message_type == "chat_message":
            chat.controls.append(ChatMesage(message))

        elif message.message_type == "login_message":
            chat.controls.append(
                ft.Text(message.text,
                        italic=True,
                        color=ft.colors.GREY_700,
                        size=12),
                        )
        elif message.message_type[:5] == "image":
            chat.controls.append(Image(message) )
        page.update()

    page.pubsub.subscribe(onMessage)

    appropriate_image_extentions = (".png", ".apng", '.avif', '.gif', '.jpg', '.jpeg', '.jfif', '.pjpeg', '.pjp', '.svg', '.webp')
    

    def unload_messages():
        chat.controls.clear()
        page.update()

    def cancel_translating(e):
        page.client_storage.set("translating", False)
        page.window_destroy()
        restart()
    
    cancel_loading_button = ft.TextButton(text = "Cancel",
                                          on_click = cancel_translating)
    if page.client_storage.get('language') != 'en':
        dialog_text, dialog_title = translate(["Please be patient", "Messages Loading"], page)
        
    else:
        dialog_text = "Please be patient the translator relies on Google Trans. It uses the Google Translate Ajax API to make calls to translate and may be slow."
        dialog_title = "          Messages Loading"
    dialog_url = "https://firebasestorage.googleapis.com/v0/b/chatapp-d1767.appspot.com/o/Infinity-1s-800px-unscreen%20(1).gif?alt=media&token=b012ecb9-749e-43de-96c7-8bbdfe924125"
    
    def load_all_messages(feedback: bool):
        
        messages = database.child(channel.name).get().val()
        
        if page.client_storage.get("translating"):
            if feedback == False:
                page.dialog = ft.AlertDialog(modal = True,
                                             title = ft.Text(dialog_title),
                                             content = ft.Column(controls = [ft.Row([ft.Text(" " * 4),ft.Image(src = dialog_url)]),
                                                                             ft.Text(dialog_text, width = 340)],
                                                                 height = 230,
                                                                 horizontal_alignment = ft.MainAxisAlignment.CENTER,
                                                                 alignment = ft.MainAxisAlignment.CENTER
                                                                ),
                                             actions = [cancel_loading_button],
                                             actions_alignment = ft.MainAxisAlignment.CENTER,
                                             shape = ft.RoundedRectangleBorder( radius = 10 )
                                            )
                page.dialog.open = True
            text_messages = list()
            mega_text_messages = list()
            
            page.update()
            for user_message in messages.values():
                  for user, message_details in user_message.items():

                      if user == 'login_message':
                          text_messages.append((f"{message_details[0]} " + "joined at" + f" {message_details[1]}"))
                      elif user.endswith("_image_base64_encoded"):
                          mega_text_messages.append(tuple(text_messages))
                          mega_text_messages.append(Image (Message(page,
                                                                   user = user[:-len("_image_base64_encoded")],
                                                                   text = message_details[0],
                                                                   message_type = "image_" + message_details[2],
                                                                   time_stamp = message_details[1],
                                                                    ),
                                                                ))
                          text_messages.clear()

                      else:               
                          text_messages.append(f"🎠{user}🎠{message_details[0]}🎠{message_details[1]}")

            if text_messages != []:
                  mega_text_messages.append(tuple(text_messages))

            for i in mega_text_messages:
                if i == ():
                    continue
                if type(i) == tuple:
                  translations = s_translate(list(i))
                  for translation in translations:
                      text = translation
                      if "🎠" in text:
                          text = text.split("🎠")
                          #To fix some random bug
                          if len(text) != 4:
                              a = text[2][-14:]
                              text[2] = text[2].replace(' ' + a,'')
                              text.append(a)
                              
                          chat.controls.append( ChatMesage (TranslatedMessage(page,
                                                            user = text[1],
                                                            text = text[2],
                                                            message_type = "chat_message",
                                                            time_stamp = text[3],
                                                            )
                                                               )
                                                  )
                      else:
                          chat.controls.append( ft.Text (text.replace("🎠",""),
                                                             italic=True,
                                                             color=ft.colors.GREY_700,
                                                             size=12,
                                                            ),
                                                  )                
                elif type(i) == Image:
                    chat.controls.append(Image (Message(page,
                                                        user = s_translate(i.user) if not i.user.isnumeric() else i.user,
                                                        text = i.text,
                                                        message_type = i.message_type,
                                                        time_stamp = i.time_stamp,
                                                            ),
                                                )) 
            
            page.dialog.open = False           
        else:
            for user_message in messages.values():
                for user, message_details in user_message.items():
                    if user == 'login_message' and channel:
                        chat.controls.append( ft.Text (f"{message_details[0]} " + "joined at" + f" {message_details[1]}",
                                                       italic=True,
                                                       color=ft.colors.GREY_700,
                                                       size=12,
                                                      ),
                                            )
                    elif user.endswith("_image_base64_encoded"):                               
                        chat.controls.append( Image (Message(page,
                                                             user = user[:-len("_image_base64_encoded")],
                                                             text = message_details[0],
                                                             message_type = "image_" + message_details[2],
                                                             time_stamp = message_details[1],
                                                            ),
                                                    )
                                            )
                    else:
                        chat.controls.append( ChatMesage (Message(page,
                                                                  user = user,
                                                                  text = message_details[0],
                                                                  message_type = "chat_message",
                                                                  time_stamp = message_details[1],
                                                                 )
                                                         )
                                            )
                    page.update()
        page.update()

    def load_messages():
        if page.client_storage.get("translating"):
            language_dropdown.value = LANGUAGES[page.client_storage.get("language")]
        messages = database.child(channel.name).get().val()

        if channel.name == "Feedback":
            if page.client_storage.get("translating"):
                page.dialog = ft.AlertDialog(modal = True,
                                             title = ft.Text(dialog_title),
                                             content = ft.Column(controls = [ft.Row([ft.Text(" " * 4),ft.Image(src = dialog_url)]),
                                                                             ft.Text(dialog_text, width = 340)],
                                                                 height = 230,
                                                                 horizontal_alignment = ft.MainAxisAlignment.CENTER,
                                                                 alignment = ft.MainAxisAlignment.CENTER
                                                                ),
                                             actions = [cancel_loading_button],
                                             actions_alignment = ft.MainAxisAlignment.CENTER,
                                             shape = ft.RoundedRectangleBorder( radius = 10 )
                                            )
                page.dialog.open = True
            page.update()
            text = s_translate("Please give your unbiased feedback as only myself and my team is able to see your messages")
            developer_message = ChatMesage (Message(page,
                                                    user = s_translate("Developer"),
                                                    text = text,
                                                    message_type = "chat_message",
                                                    time_stamp = "0/0/0 0:0",
                                                    ))
            chat.controls.append( developer_message )
            if messages:
                if page.session.get("username") == '123':
                    load_all_messages(True)
                else:    
                    for user_message in messages.values():
                        to = "To " + page.session.get("username") + ' '
                        for user, message_details in user_message.items():
                            load = False
                            if user == page.session.get("username"):
                                load = True
                                
                            elif message_details[0].startswith(to):
                                message_details[0] = message_details[0].replace(to, '')
                                load = True
                                
                            if load == True:
                                text = s_translate(message_details[0])
                                chat.controls.append( ChatMesage (Message(page,
                                                                          user = user,
                                                                          text = text,
                                                                          message_type = "chat_message",
                                                                          time_stamp = message_details[1],
                                                                         )
                                                                 )
                                                    )
                    page.dialog.open = False
            page.update()

        elif messages:
            load_all_messages(False)

    create_email = ft.TextField(hint_text = s_translate("Enter email"),
                                   on_submit = lambda e: create_password.focus(),
                                   )
    create_password = ft.TextField(hint_text = s_translate("Enter password"),
                                   on_submit = lambda e: confirm_create_password.focus(),
                                   password = True,
                                   can_reveal_password = True
                                   )
    confirm_create_password = ft.TextField(hint_text = s_translate("Confirm password"),
                                           on_submit = create_account,
                                           password = True,
                                           can_reveal_password = True
                                           )
    create_username = ft.TextField(hint_text = s_translate("Enter username"),
                                   on_submit = lambda e: create_email.focus(),
                                   autofocus = True,
                                   )
    login_password = ft.TextField(hint_text = s_translate("Enter password"),
                                  on_submit = login,
                                  password = True,
                                  autofocus =  page.client_storage.contains_key("username"),
                                  can_reveal_password = True
                                  )                           
    login_username = ft.TextField(hint_text = s_translate("Enter username"),
                                  value = page.client_storage.get("username"),
                                  on_submit = lambda e: login_password.focus(),
                                  autofocus = not page.client_storage.contains_key("username"),
                                 )
    auto_login_checkbox =ft.Checkbox(label="Stay logged in", value = page.client_storage.get("Stay logged in"))
    
    login_dialog = ft.AlertDialog(modal = True,
                                  shape = ft.RoundedRectangleBorder( radius = 10 ),
                                  title = ft.Text(s_translate("Log-in") + ' ' * 50),
                                  content = ft.Column( [login_username, login_password, auto_login_checkbox], tight = True ),
                                  actions = [ft.Row( [ft.TextButton(s_translate("Create account"), on_click =  open_create_account),
                                                      ft.TextButton(s_translate("Join"), on_click =  login),
                                                     ],
                                                     alignment = ft.MainAxisAlignment.SPACE_BETWEEN
                                                   ),
                                            ],
                                  actions_alignment = ft.MainAxisAlignment.END,
                                  )
    
    chat = ft.ListView(expand=True,
                       spacing=10,
                       auto_scroll=True,
                       )
    new_message = ft.TextField(hint_text = s_translate("Write a message"),
                               autofocus = True,
                               shift_enter = True,
                               filled = True,
                               expand = True,
                               on_submit = send_clicked,
                               )
    send_button = ft.ElevatedButton(s_translate("Send"),
                                    on_click = send_clicked,
                                    )

    chat_container = ft.Container(content=chat,
                                  border=ft.border.all(1, ft.colors.OUTLINE),
                                  padding = 5,
                                  expand=True,
                                  )
    message_sender = ft.Row([new_message,
                             send_button,
                            ],
                            )

    def on_keyboard(e: ft.KeyboardEvent):
            if e.ctrl and not e.shift and e.key == 'T':
                    shortcut_theme_change()
            if not page.session.get("logged in"):
                return None
            if e.key == "Escape":
                page.drawer.open = True
                page.update()
            elif e.key == "Enter":
                new_message.focus()
            elif e.ctrl:
                if e.key == 'I':
                    shortcut_upload_image()
                elif e.shift:
                    if e.key == 'T':
                        shortcut_open_translator()
                    
    page.on_keyboard_event = on_keyboard

    def page_resize(e):
        page.update()
    page.on_resize = page_resize

    page.appbar = ft.AppBar(
        leading = ft.IconButton(ft.icons.MENU, 
                                on_click = show_drawer,
                                tooltip = s_translate("Menu") + "(press esc)",
                                icon_size = 30,
                               ),
        leading_width = 50,
        title = ft.Text(s_translate("Global Chat")),
        center_title = False,
        bgcolor = ft.colors.BLACK87,
        actions = [
            translate_iconbutton,
            theme_swich,
            upload_image_button,   
        ],)
