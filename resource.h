#pragma once

// Menu
#define IDR_MAINMENU        100

// Dialogs
#define IDD_TASKDIALOG      101

// Menu / Toolbar commands
#define ID_FILE_EXIT        40001
#define ID_TASK_ADD         40010
#define ID_TASK_EDIT        40011
#define ID_TASK_DELETE      40012
#define ID_TASK_START       40020
#define ID_TASK_STOP        40021

// Dialog controls
#define IDC_WINDOWTITLE     1001
#define IDC_CAPTUREWINDOW   1002
#define IDC_POSX            1003
#define IDC_POSY            1004
#define IDC_GETMOUSEPOS     1005
#define IDC_TRIGGERDATE     1006
#define IDC_TRIGGERTIME     1007
#define IDC_OFFSET          1008
#define IDC_INTERVAL        1009
#define IDC_REPEAT          1010
#define IDC_RADIO_BG        1011
#define IDC_RADIO_FG        1012
#define IDC_RADIO_LEFT      1013
#define IDC_RADIO_RIGHT     1014

// ListView columns (not resource IDs, but grouped here for reference)
#define LV_COL_TIME         0
#define LV_COL_WINDOW       1
#define LV_COL_POS          2
#define LV_COL_INTERVAL     3
#define LV_COL_STATUS       4
