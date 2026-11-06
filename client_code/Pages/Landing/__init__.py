from anvil import *

from ._anvil_designer import LandingTemplate
from ... import router, state

# The app's video on the Addanapp YouTube channel (APP_MAKER/youtube/manifest.json), shown in the Watch section.
YT_VIDEO = "Eex4sJbZDNg"


class Landing(LandingTemplate):
    """#landing (Persuade): the rolling-cover hero on Mom's gingham cloth (the pan changes dish with the headline; the
    picture is static SVG in the template), the Watch section (the YouTube video), how it works, the rules, questions
    and the closing band. "Peek at a week" opens Dialogs/Peek (sample_week, nothing saved). Copy lives in the template."""

    def __init__(self, args=(), **properties):
        super().__init__(**properties)
        me = state.me()
        self.guest_cta.visible = not me
        self.member_cta.visible = bool(me)
        self.band_guest.visible = not me
        self.band_member.visible = bool(me)
        self.dom_nodes["yt_cover"].addEventListener("click", self._play)

    def _play(self, event):
        """Swap the video's cover for YouTube's player (privacy-enhanced); nothing loads from YouTube before this click."""
        self.dom_nodes["yt_frame"].innerHTML = (
            '<iframe src="https://www.youtube-nocookie.com/embed/' + YT_VIDEO + '?autoplay=1&rel=0&playsinline=1" '
            'title="Topameal video" allow="autoplay; encrypted-media; picture-in-picture; fullscreen" allowfullscreen '
            'referrerpolicy="strict-origin-when-cross-origin"></iframe>')

    @handle("peek_button", "click")
    def peek_button_click(self, **event_args):
        from ...Dialogs.Peek import Peek
        if alert(Peek(), buttons=[], role="app-dialog", dismissible=True) == "signup":
            router.go("auth", "signup")
