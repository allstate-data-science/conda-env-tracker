"""Interacting with conda channels."""

from typing import Union

from conda_env_tracker.types import ListLike


class Channels(list):
    """The conda channels used when creating the environment."""

    def __init__(self, channels: Union[str, ListLike] = None):
        if isinstance(channels, str):
            channels = [channels]
        if channels:
            list.__init__(self, channels)
        else:
            list.__init__(self)

    def create_channel_command(
        self, preferred_channels: ListLike = None, strict_channel_priority: bool = True
    ) -> str:
        """Return channels to be used in conda command.

        If strict_channel_priority=True then do not use extra flags such as "--strict-channel-priority".
        """
        if not preferred_channels:
            channels_string = self.format_channels(self)
        else:
            channels_list = self.compute_effective_channels(preferred_channels, self)
            channels_string = self.format_channels(channels_list)
        if strict_channel_priority:
            flags = ["--override-channels", "--strict-channel-priority"]
        else:
            flags = ["--override-channels"]
        return " ".join(flags) + " " + channels_string

    @staticmethod
    def format_channels(channels: ListLike) -> str:
        """A utility function for formatting the channel string"""
        return " ".join("--channel " + channel for channel in channels)

    @staticmethod
    def compute_effective_channels(
        primary_channels: ListLike, secondary_channels: ListLike
    ) -> ListLike:
        """This function computes the effective channel order based on two lists of channels."""
        if primary_channels:
            effective_channels = list(primary_channels)
        else:
            effective_channels = []
        for channel in secondary_channels:
            if channel not in effective_channels:
                effective_channels.append(channel)
        return effective_channels

    def export(self):
        """Export as list instead of subclass."""
        if not self:
            return []
        return list(self)
