# Copyright (c) 2024 - Gilles Coissac
# This file is part of standard-deluxe library.
#
# standard-deluxe is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published
# by the Free Software Foundation, either version 3 of the License,
# or (at your option) any later version.
#
# standard-deluxe is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty
# of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with standard-deluxe. If not, see <https://www.gnu.org/licenses/>
#
"""Binding for the Windows shell32.dll function SHGetKnownFolderPath.

This module provides a high-level, Pythonic interface to retrieve the full
paths of "Known Folders" (e.g., Downloads, Documents, Pictures) on Windows.
It handles all necessary :mod:`ctypes` definitions, pointer manipulation, and
memory management, ensuring robustness and safety.

The main interface is the :class:`KnownFolderID` enum, which enumerates
standard folder GUIDs and provides a :attr:`KnownFolderID.path` property that
returns the full path for each folder.
"""

from __future__ import annotations

import ctypes
import enum
import uuid
from ctypes import wintypes
from enum import Enum
from typing import final

from deluxe.availability import availability, supported


__all__ = ("GUID", "KnownFolderID")


@final
class GUID(ctypes.Structure):
    """Define a GUID structure for representing KNOWNFOLDERID values.

    This class wraps the Windows GUID (Globally Unique Identifier) structure,
    which is used to identify "Known Folders" in the Windows shell. It provides
    a Python-friendly way to create GUID instances from string representations.

    The structure is defined as required by the Windows API and is used in
    conjunction with the :func:`shell32.SHGetKnownFolderPath` function to
    retrieve folder paths.

    Attributes:
        Data1 (:class:`wintypes.DWORD`): The first 4 bytes of the GUID.
        Data2 (:class:`wintypes.WORD`): Bytes 5-6 of the GUID.
        Data3 (:class:`wintypes.WORD`): Bytes 7-8 of the GUID.
        Data4 (:class:`wintypes.BYTE` * 8): The final 8 bytes of the GUID.

    Args:
        guid_string (:obj:`str`): A string representation of the GUID in the
            standard format (e.g., ``"008ca0b1-55b4-4c56-b8a8-4de4b299d3be"``).
    """

    _fields_ = [
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD),
        ("Data3", wintypes.WORD),
        ("Data4", wintypes.BYTE * 8),
    ]

    def __init__(self, guid_string: str) -> None:
        # The from_buffer_copy method is an efficient way to initialize
        # the structure from a raw byte representation of the GUID.
        # This avoids manual field-by-field assignment.
        super().__init__()
        ctypes.memmove(
            ctypes.byref(self),
            uuid.UUID(guid_string).bytes_le,
            16,
        )


if supported("windows"):  # pragma: posix no cover
    # HRESULT is a common return type in COM and Win32 API,
    # indicating success/failure. S_OK (0) indicates success.
    HRESULT = wintypes.HRESULT  # pyright: ignore[reportUnknownVariableType, reportUnknownMemberType, reportAttributeAccessIssue]
    PWSTR = ctypes.c_wchar_p  # pointer to a wide-character (Unicode) string.

    try:
        shell32 = ctypes.WinDLL("shell32")  # for SHGetKnownFolderPath.
        ole32 = ctypes.WinDLL("ole32")  # for CoTaskMemFree
    except OSError as e:
        msg = "Failed to load shell32.dll or ole32.dll"
        raise ImportError(msg) from e

    _SHGetKnownFolderPath = shell32.SHGetKnownFolderPath
    _SHGetKnownFolderPath.argtypes = [
        ctypes.POINTER(GUID),  # rfid: A pointer to the KNOWNFOLDERID
        wintypes.DWORD,  # dwFlags: Flags, 0 for default behavior
        wintypes.HANDLE,  # hToken: User token, None for current user
        ctypes.POINTER(PWSTR),  # ppszPath: A pointer to receive the path string
    ]
    _SHGetKnownFolderPath.restype = HRESULT

    _CoTaskMemFree = ole32.CoTaskMemFree
    _CoTaskMemFree.argtypes = [wintypes.LPVOID]  # A generic pointer
    _CoTaskMemFree.restype = None


@availability(only="windows")
class KnownFolderID(Enum):
    """Enumerate GUID constants identifying Windows Known Folders.

    Known Folders are standard folders registered with the system that have
    well-defined locations on Windows. These include per-user folders (e.g.,
    Desktop, Documents, Downloads), common folders shared across all users
    (e.g., Public Documents), and fixed system folders (e.g., Program Files,
    Windows).

    The GUIDs in this enum are used with the Windows
    ``SHGetKnownFolderPath`` API to retrieve the full path of each folder.

    Note:
        Known Folders are installed with Windows Vista and later operating
        systems. A computer will have only folders appropriate to it installed.

    See:
        `Known Folder ID Reference <https://learn.microsoft.com/en-us/windows/win32/shell/knownfolderid>`__
    """

    # --- Per-user folders ---
    AccountPictures = GUID("{008ca0b1-55b4-4c56-b8a8-4de4b299d3be}")
    AppDataDesktop = GUID("{B250C668-4275-467C-9047-403681E83733}")
    AppDataDocuments = GUID("{7D1D3A04-DEBB-4115-95CF-2F29DA2920DA}")
    AppDataFavorites = GUID("{1E4887BE-143B-4958-B632-3425E34A7836}")
    AppDataProgramData = GUID("{F1752C83-AE4B-487A-A33B-A7A255DAB763}")
    AppDataSearches = GUID("{0138D53A-6AFE-4586-8655-75783A553408}")
    CameraRoll = GUID("{AB5FB87B-7CE2-4F83-915D-550846C9537B}")
    Contacts = GUID("{56784854-C6CB-462B-8169-88E350ACB882}")
    Cookies = GUID("{2B0F765D-C0E9-4171-908E-08A611B84FF6}")
    Desktop = GUID("{B4BFCC3A-DB2C-424C-B029-7FE99A87C641}")
    Documents = GUID("{FDD39AD0-238F-46AF-ADB4-6C85480369C7}")
    Downloads = GUID("{374DE290-123F-4565-9164-39C4925E467B}")
    Favorites = GUID("{1777F761-68AD-4D8A-87BD-30B759FA33DD}")
    History = GUID("{D9DC8A3B-B784-432E-A781-5A1130A75963}")
    InternetCache = GUID("{352481E8-33BE-4251-BA85-6007CAEDCF9D}")
    Links = GUID("{BFB9D5E0-C6A9-404C-B2B2-AE6DB6AF4968}")
    LocalAppData = GUID("{F1B32785-6FBA-4FCF-9D55-7B8E7F157091}")
    LocalAppDataLow = GUID("{A520A1A4-1780-4FF6-BD18-167343C5AF16}")
    Music = GUID("{4BD8D571-6D19-48D3-BE97-422220080E43}")
    NetHood = GUID("{C5ABBF53-E17F-4121-8900-86626FC2C973}")
    Objects3D = GUID("{31C0DD25-9439-4F12-BF41-7FF4EDA38722}")
    Pictures = GUID("{33E28130-4E1E-4356-B050-37D5425CE744}")
    Playlists = GUID("{DE92C1C7-837F-4F69-A3BB-86E631204A23}")
    PrintHood = GUID("{9274BD8D-CFD1-41C3-B35E-B13F55A758F4}")
    Profile = GUID("{5E6C858F-0E22-4760-9AFE-EA3317B67173}")
    RoamingAppData = GUID("{3EB685DB-65F9-4CF6-A03A-E3EF65729F3D}")
    SavedGames = GUID("{4C5C32FF-BB9D-43B0-B5B4-2D72E54EAAA4}")
    Screenshots = GUID("{B7BEDE81-DF94-4682-A7D8-57A52620B86F}")
    Searches = GUID("{7d1d3a04-debb-4115-95cf-2f29da2920da}")
    SendTo = GUID("{8983036C-27C0-404B-8F08-102D10DCFD74}")
    StartMenu = GUID("{625B53C3-AB48-4EC1-BA1F-A1EF4146FC19}")
    Startup = GUID("{B97D20BB-F46A-4C97-BA10-5E3608430854}")
    Templates = GUID("{A63293E8-664E-48DB-A079-DF759E0509F7}")
    Videos = GUID("{18989B1D-99B5-455B-841C-AB7C74E4DDFC}")

    # Per-user application data
    AppDataLocal = GUID("{F1B32785-6FBA-4FCF-9D55-7B8E7F157091}")  # noqa: PIE796
    AppDataRoaming = GUID("{3EB685DB-65F9-4CF6-A03A-E3EF65729F3D}")  # noqa: PIE796

    # --- Common folders (all users) ---
    CommonAdminTools = GUID("{D0384E7D-BAC3-4797-8F14-CBA229B392B5}")
    CommonOemLinks = GUID("{C1BAE2D0-10DF-4334-BEDD-7AA20B227A9D}")
    CommonPrograms = GUID("{0139D44E-6AFE-49F2-8690-3DAFCAE6FFB8}")
    CommonStartMenu = GUID("{A4115719-D62E-491D-AA7C-E74B8BE3B067}")
    CommonStartup = GUID("{82A5EA35-D9CD-47C5-9629-E15D2F714E6E}")
    CommonTemplates = GUID("{B94237E7-57AC-4347-9151-B08C6C32D1F7}")
    Public = GUID("{DFDF76A2-C82A-4D63-906A-5644AC457385}")
    PublicDesktop = GUID("{C4AA340D-F20F-4863-AFEF-F87EF2E6BA25}")
    PublicDocuments = GUID("{ED4824AF-DCE4-45A8-81E2-FC7965083634}")
    PublicDownloads = GUID("{3D644C9B-1FB8-4F30-9B45-F670235F79C0}")
    PublicGameTasks = GUID("{DEBF2536-E1A8-4C59-B6A2-414586476AEA}")
    PublicMusic = GUID("{3214FAB5-9757-4298-BB61-92A9DEAA44FF}")
    PublicPictures = GUID("{B6EBFB86-6907-413C-9AF7-4FC2ABF07CC5}")
    PublicVideos = GUID("{2400183A-6185-49FB-A2D8-4A392A602BA3}")
    ResourceDir = GUID("{8AD10C31-2ADB-4296-A8F7-E4701232C972}")

    # --- Fixed folders ---
    CDBurning = GUID("{9E52AB10-F80D-49DF-ACB8-4330F5687855}")
    DeviceMetadataStore = GUID("{5CE4A5E9-E4EB-479D-B89F-130C02886155}")
    Fonts = GUID("{FD228CB7-AE11-4AE3-864C-16F3910AB8FE}")
    ProgramData = GUID("{62AB5D82-FDC1-4DC3-A9DD-070D1D495D97}")
    ProgramFiles = GUID("{905e63b6-c1bf-494e-b29c-65b732d3d21a}")
    ProgramFilesX64 = GUID("{6D809377-6AF0-444b-8957-A3773F02200E}")
    ProgramFilesX86 = GUID("{7C5A40EF-A0FB-4BFC-874A-C0F2E0B9FA8E}")
    ProgramFilesCommon = GUID("{F7F1ED05-9F6D-47A2-AA7D-2B6718265DA9}")
    ProgramFilesCommonX64 = GUID("{6365D5A7-0F0D-45E5-87F6-0DA56B6A4F7D}")
    ProgramFilesCommonX86 = GUID("{DE974D24-D9C6-4D3E-BF91-F4455120B917}")
    System = GUID("{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}")
    SystemX86 = GUID("{D65231B0-B2F1-4857-A4CE-A8E7C6EA7D27}")
    UserProfiles = GUID("{0762D272-C50A-4BB0-A382-697DCD729B80}")
    Windows = GUID("{F38BF404-1D43-42F2-9305-67DE0B28FC23}")

    # --- Virtual folders ---
    AddNewPrograms = GUID("{DE61D048-5EB4-4504-A3A9-A7C7C2F275C4}")
    AppUpdates = GUID("{A305CE99-F527-492B-8B1A-7E76FA98D6E4}")
    ChangeRemovePrograms = GUID("{DF7266AC-9274-4867-8D55-3BD661DE872D}")
    ComputerFolder = GUID("{0AC0837C-4BF2-450B-8A82-0D644FF69D78}")
    ConflictFolder = GUID("{4bfefb45-347d-4006-a5be-ac0cb0567192}")
    ControlPanelFolder = GUID("{82A74AEB-AEB4-465C-A014-D097EE346D63}")

    # Note: ControlPanelFolder and NetworkFolder have the same GUID in docs
    # but different names. Enum members must be unique. Let's alias it.
    NetworkFolder = ControlPanelFolder
    Games = GUID("{CAC52C1A-B53D-4EDC-92D7-6B2E8AC19434}")
    GameTasks = GUID("{054FAE61-4DD8-4787-80B6-090220C4B700}")
    HomeGroup = GUID("{B4FB3F98-C1EA-428d-A78A-D1F5659CBA93}")
    HomeGroupCurrentUser = GUID("{9B74B6A3-0DFD-4f11-9E78-5F7800F2E772}")
    Libraries = GUID("{1B3EA5DC-B587-4786-B4EF-BD1DC332AEAE}")
    NetworkShortcuts = GUID("{C5ABBF53-E17F-4121-8900-86626FC2C973}")  # noqa: PIE796
    PrintersFolder = GUID("{76166B06-3D3C-451A-A395-6C98520B96A8}")
    Recent = GUID("{AE50C081-EBD2-438A-8655-8A092E34987A}")
    RecycleBinFolder = GUID("{B7534046-3ECB-4C18-BE4E-64CD4CB7D6AC}")
    Ringtones = GUID("{C870044B-F49E-4126-A9C3-B52A1FF411E8}")
    SearchConnectorFolder = GUID("{0B474434-3A42-440D-94F0-2B6B415EA75B}")
    SearchHome = GUID("{190337d1-59c3-4283-b9c0-68f799bad447}")
    SyncManagerFolder = GUID("{43668BF8-8D55-49A9-B943-AD4649A97375}")
    ThisPC = GUID("{20D04FE0-3AEA-1069-A2D8-08002B30309D}")
    UsersFiles = GUID("{f3ce0f7c-4901-4acc-8648-d5d44b04ef8f}")
    UsersLibraries = GUID("{A302545D-DEFF-464b-ABE8-61C8648D939B}")

    @enum.property
    @availability(only="windows")
    def path(self) -> str:  # pragma: posix no cover
        """Retrieve the full file system path of the Known Folder.

        This property provides a high-level Python wrapper around the Windows
        ``SHGetKnownFolderPath`` API function. It retrieves the full path of the
        folder identified by the current enum member.

        The function handles all necessary memory management, including proper
        cleanup of the allocated string buffer using ``CoTaskMemFree``.

        Returns:
            :obj:`str`: The full path of the Known Folder on the file system.

        Raises:
            :exc:`ctypes.WinError`: If the underlying Windows API call fails
                for any reason (e.g., the folder does not exist on the current
                system, insufficient permissions, or invalid parameters).
        """  # noqa: DOC501
        path_ptr = PWSTR()
        hresult = _SHGetKnownFolderPath(ctypes.byref(self.value), 0, None, ctypes.byref(path_ptr))

        if hresult != 0 or (result := path_ptr.value) is None:
            raise ctypes.WinError(hresult)
        _CoTaskMemFree(path_ptr)
        return result

    def __fspath__(self) -> str:
        return self.path
