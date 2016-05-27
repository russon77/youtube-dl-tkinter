from tkinter import *
from tkinter.filedialog import askdirectory
from threading import Thread
import os
import youtube_dl
import re


class VideoDownload(object):
    def __init__(self, url, download_opts, path="/"):
        self.url = url
        self.download_opts = download_opts
        self.path = path

        self.status = {
            "status": "getting metadata..."
        }

        self.info = None

    def __str__(self):
        if self.info:
            return "%s | %s" % (self.info.get("title", self.url), self.status["status"])
        else:
            return "%s | %s" % (self.url, self.status["status"])


class MyApp(object):
    def __init__(self, master):
        # master container
        overlord_frame = Frame(master)
        overlord_frame.pack(fill=BOTH, expand=1)

        # buttons frame
        self.buttons_frame = Frame(overlord_frame)
        self.buttons_frame.pack(fill=X)

        self.button_add_video = Button(self.buttons_frame, text="Add", command=self.new_single_video_callback)
        self.button_add_video.pack(side=LEFT)

        self.button_add_video_in_bulk = Button(self.buttons_frame, text="Add bulk")
        self.button_add_video_in_bulk.pack(side=LEFT)

        # these are context-sensitive buttons. i.e they will only work if the user has selected something in the
        #  listbox
        self.button_remove_download_from_list = Button(self.buttons_frame, text="Remove")
        self.button_remove_download_from_list.pack(side=LEFT)

        # add in our list box -- to the master reference
        self.videos_listbox = Listbox(master, selectmode=EXTENDED, exportselection=0)
        self.videos_listbox.pack(fill=BOTH, expand=1)

        self.videos_listbox.bind("<Double-Button-1>", lambda x: print(self.videos_listbox.curselection()))

        # initialize our list of current video downloads
        self.videos = []

        # start the regular ui updates
        self.update_video_ui_repeating(master)

    def update_video_ui_repeating(self, widget):
        # to update the listbox, remove all elements and then re-insert them
        # if this were an expensive operation, we could check if there is any difference in state between updates
        self.videos_listbox.delete(0, END)
        self.videos_listbox.insert(END, *[str(x) for x in self.videos])

        # update again in one second.
        widget.after(1, lambda: self.update_video_ui_repeating(widget))

    @staticmethod
    def download_progress_hook(video_download, status):
        video_download.status = status

    @staticmethod
    def start_download(video_download):
        # get the video metadata
        with youtube_dl.YoutubeDL({}) as ydl:
            info_dict = ydl.extract_info(video_download.url, download=False)
            video_download.info = info_dict

        # now download the actual video
        ydl_opts = {
            "progress_hooks": [lambda x: MyApp.download_progress_hook(video_download, x)],
            **video_download.download_opts
        }
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_download.url])

    def create_video_download(self, url, download_opts):
        video_download = VideoDownload(url, download_opts)
        self.videos.append(video_download)
        thread = Thread(target=self.start_download, args=(video_download,))
        thread.start()

    def submit_new_video_for_download(self, frame, url, destination, on_success):
        error = None

        # we are passed references to functions containing the values
        url = url()
        destination = destination()

        # check for valid url
        if not re.match(r"https?:\/\/(www\.)?youtube.com\/watch\?v=\w+", url):
            # add in error to bottom of frame
            error = Label(frame, text="Not a Youtube URL")
        # check for valid save location
        elif False:
            pass

        if error:
            error.pack()

            return

        # outtmpl is the template to use when writing the video file to disk
        opts = {
            'outtmpl': os.path.join(destination, '%(title)s-%(id)s.%(ext)s')
        }

        # okay, all checks pass
        self.create_video_download(url, opts)

        on_success()

    def new_single_video_callback(self):
        top = Toplevel()
        top.title("New download")
        top.resizable(False, False)

        # set up the add video dialog box
        frame_url = Frame(top)
        frame_url.pack()

        msg_url = Message(frame_url, text="URL")
        msg_url.pack(side=LEFT)

        e = Entry(frame_url)
        e.pack(side=LEFT)

        frame_destination = Frame(top)
        frame_destination.pack()

        # todo more options

        # using a StringVar allows us to easily update the Label, in addition to storing the destination path
        dest_label = Label(frame_destination, text="Target")
        dest_label.pack()

        path_var = StringVar(value="/your/path/here/")
        path_lbl = Label(frame_destination, textvariable=path_var)
        path_lbl.pack(side=LEFT, fill=X)
        path_lbl.bind("<Button-1>", lambda _: path_var.set(askdirectory()))

        frame_actions = Frame(top)
        frame_actions.pack()

        submit = Button(frame_actions,
                        text="Go",
                        command=lambda: self.submit_new_video_for_download(top, e.get, path_var.get, top.destroy))
        submit.pack(side=LEFT)

        cancel = Button(frame_actions, text="Cancel", command=top.destroy)
        cancel.pack(side=LEFT)

# initialize tkinter
root = Tk()

# create an instance of our application with root as the main container
app = MyApp(root)

# run the event loop
root.mainloop()

# cleanup is unnecessary, Python handles this at the end of a script
