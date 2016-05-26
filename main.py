from tkinter import *
from tkinter.filedialog import askdirectory
from threading import Thread
import os
import youtube_dl


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
        self.videos_listbox.delete(0, END)
        self.videos_listbox.insert(END, *[str(x) for x in self.videos])
        self.videos_listbox.pack()

        widget.after(1, lambda: self.update_video_ui_repeating(widget))

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

    def progress_hook_experiment(self, d):
        pass

    @staticmethod
    def download_progress_hook(video_download, status):
        video_download.status = status

    def create_video_download(self, url, download_opts, callback):
        video_download = VideoDownload(url, download_opts)
        self.videos.append(video_download)
        thread = Thread(target=self.start_download, args=(video_download,))
        thread.start()
        callback()

    def new_single_video_callback(self):
        top = Toplevel()
        top.title("New download")

        msg = Message(top, text="URL")
        msg.pack(side=LEFT)

        e = Entry(top)
        e.pack(side=LEFT)

        # todo optional options for download
        # todo download path / destination

        path = StringVar(value="/")
        path_lbl = Label(top, textvariable=path)
        path_lbl.pack()

        d = Button(top, text="download location", command=lambda: path.set(askdirectory()))
        d.pack(side=BOTTOM)


        opts = {
            'outtmpl': os.path.join(path.get(), '%(title)s-%(id)s.%(ext)s')
        }

        submit = Button(top, text="Go", command=lambda: self.create_video_download(e.get(), opts, top.destroy))
        submit.pack(side=LEFT)

root = Tk()

app = MyApp(root)

root.mainloop()
