from tkinter import *
from tkinter.filedialog import askdirectory
from tkinter.ttk import Treeview
from threading import Thread
import os
import youtube_dl
import re
import subprocess
import sys

# from stackoverflow -- with a few modifications
# http://stackoverflow.com/questions/6631299/python-opening-a-folder-in-explorer-nautilus-mac-thingie
if sys.platform == 'darwin':
    def open_folder(path):
        subprocess.check_call(['open', '--', path])
elif sys.platform == 'linux':
    def open_folder(path):
        subprocess.check_call(['xdg-open', path])
elif sys.platform == 'win32':
    def open_folder(path):
        subprocess.check_call(['explorer', path])


class VideoDownload(object):
    def __init__(self, url, download_opts, path):
        self.url = url
        self.download_opts = download_opts
        self.path = path

        self.status = {
            "status": "getting metadata..."
        }

        self.info = None

        self.tree_id = None

    def to_columns(self):
        if self.info is None:
            return self.url, self.status["status"], "", "", ""

        percent = "unknown"
        if self.status["status"] == "finished":
            percent = "100%"
        elif self.status.get("downloaded_bytes", None) and self.status.get("total_bytes", None):
            percent = "%.2f%%" % (self.status["downloaded_bytes"] / self.status["total_bytes"] * 100.0)

        # todo format speed
        speed = ""
        if self.status.get("speed"):
            speed = "%.1f kB/s" % (self.status["speed"] / 1000.0)

        eta = ""
        if self.status.get("eta"):
            seconds = self.status["eta"]

            if seconds > 3600:
                eta = ">1 hour"
            elif seconds > 60:
                eta = "%d:%2d" % (seconds / 60, seconds % 60)
            else:
                eta = "%2d" % seconds

        return self.info.get("title", self.url), \
               self.status["status"], \
               percent, \
               speed, \
               eta, \
               self.status.get("error", "")

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

        # these are context-sensitive buttons. i.e they will only work if the user has selected something in the
        #  listbox
        self.button_remove_download_from_list = Button(self.buttons_frame, text="Remove", command=self.on_remove)
        self.button_remove_download_from_list.pack(side=LEFT)

        # let's switch it up and use a treeview
        self.videos_treeview = Treeview(master,
                                        selectmode=EXTENDED,
                                        columns=('Name', 'Status', 'Percent', 'Speed', 'Remaining', 'Error'))
        self.videos_treeview.bind("<Double-1>", self.on_treeview_double_click)

        [self.videos_treeview.heading(x, text=x) for x in self.videos_treeview['columns']]
        self.videos_treeview.column("#0", width=10)

        self.videos_treeview.pack(fill=BOTH, expand=1)

        # initialize our list of current video downloads
        self.videos_not_displayed = []
        self.videos_displayed = {}

        # start the regular ui updates
        self.update_video_ui_repeating(master)

    def on_remove(self):
        indices = self.videos_treeview.selection()

        for index in indices:
            self.videos_displayed.pop(index, None)
            self.videos_treeview.delete(index)

    def on_treeview_double_click(self, event):
        index = self.videos_treeview.focus()

        if index == "":
            return

        selection = self.videos_displayed[index]

        path = selection.path

        open_folder(path)

    def update_video_ui_repeating(self, widget):
        # hoorah, we did it the right way!
        children = self.videos_treeview.get_children()
        for child in children:
            self.videos_treeview.item(child, text="", values=self.videos_displayed[child].to_columns())

        # process any videos not currently in the tree:
        #  add them to the tree, saving the id
        #  add the video to the hash table holding them
        for vid in self.videos_not_displayed:
            key = self.videos_treeview.insert("", "end", text="", values=vid.to_columns())
            self.videos_displayed[key] = vid

        self.videos_not_displayed.clear()

        # update again in 500 ms.
        widget.after(500, lambda: self.update_video_ui_repeating(widget))

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

    def create_video_download(self, url, download_opts, path):
        video_download = VideoDownload(url, download_opts, path)
        self.videos_not_displayed.append(video_download)
        thread = Thread(target=self.start_download, args=(video_download,))
        thread.start()

    def submit_new_video_for_download(self, frame, url, destination, on_success):
        error = None

        # we are passed references to functions containing the values
        url = url()
        destination = destination()

        # check for valid url
        if not re.match(r"https?://(www\.)?youtube.com/watch\?v=\w+", url):
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
        self.create_video_download(url, opts, destination)

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
        # fancy lambdas to prevent emptying `path_var` upon cancelling the dialog
        path_lbl.bind("<Button-1>",
                      lambda _: path_var.set(
                          (lambda d: d if len(d) else path_var.get())(askdirectory())))

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
