"""Handle CHZZK single-file DASH byte-range metadata without changing requests.

Initialization@sourceURL and SegmentURL@media can be absent when the ranges
refer to the Representation's BaseURL. yt-dlp assumes both are present.
For this specific single-resource form, expose the complete media resource
as a direct format, preserving codec/quality metadata and FFmpeg section cuts.
Other manifest forms retain upstream parsing, rather than guessing URLs.
"""
from copy import deepcopy


def install_chzzk_dash_compat():
    from yt_dlp.extractor.chzzk import CHZZKVideoIE
    if getattr(CHZZKVideoIE, '_clipcatcher_dash_compat', False):
        return
    original = CHZZKVideoIE._parse_mpd_periods

    def parse(self, mpd_doc, *args, **kwargs):
        normalized = deepcopy(mpd_doc)
        for parent in normalized.iter():
            for segment_list in list(parent):
                if segment_list.tag.rsplit('}', 1)[-1] != 'SegmentList':
                    continue
                init = next((node for node in segment_list
                             if node.tag.rsplit('}', 1)[-1] == 'Initialization'), None)
                if init is None or 'sourceURL' in init.attrib:
                    continue
                segments = [node for node in segment_list
                            if node.tag.rsplit('}', 1)[-1] == 'SegmentURL']
                base = next((node for node in parent
                             if node.tag.rsplit('}', 1)[-1] == 'BaseURL'), None)
                # Only the proved single-resource representation is flattened.
                # Keep protection elements intact; never discard DRM metadata.
                if (base is not None and base.text and segments
                        and all(not node.get('media') for node in segments)
                        and init.get('range')
                        and all(node.get('mediaRange') for node in segments)):
                    parent.remove(segment_list)
        yield from original(self, normalized, *args, **kwargs)

    CHZZKVideoIE._parse_mpd_periods = parse
    CHZZKVideoIE._clipcatcher_dash_compat = True
