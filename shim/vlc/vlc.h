// [wasm-port] VLC is not available on Emscripten. Every libvlc_* call becomes a no-op so that
// VideoSprite.cpp compiles and links unchanged; the real player will be rewritten on top of <video>.
#ifndef __SHIM_VLC_H__
#define __SHIM_VLC_H__
#ifdef __cplusplus
extern "C" {
#endif
typedef struct libvlc_instance_t libvlc_instance_t;
typedef struct libvlc_media_t libvlc_media_t;
typedef struct libvlc_media_player_t libvlc_media_player_t;
typedef struct libvlc_event_manager_t libvlc_event_manager_t;
typedef int libvlc_event_type_t;
typedef int libvlc_state_t;
typedef struct libvlc_event_t { libvlc_event_type_t type; } libvlc_event_t;
#define libvlc_MediaPlayerEndReached 0
#define libvlc_new(...)                       ((libvlc_instance_t*)0)
#define libvlc_release(...)                   ((void)0)
#define libvlc_media_new_path(...)            ((libvlc_media_t*)0)
#define libvlc_media_add_option(...)          ((void)0)
#define libvlc_media_release(...)             ((void)0)
#define libvlc_media_player_new_from_media(...) ((libvlc_media_player_t*)0)
#define libvlc_media_player_release(...)      ((void)0)
#define libvlc_media_player_stop(...)         ((void)0)
#define libvlc_media_player_play(...)         ((void)0)
#define libvlc_media_player_set_pause(...)    ((void)0)
#define libvlc_media_player_get_state(...)    ((libvlc_state_t)0)
#define libvlc_media_player_event_manager(...) ((libvlc_event_manager_t*)0)
#define libvlc_video_set_callbacks(...)       ((void)0)
#define libvlc_video_set_format(...)          ((void)0)
#define libvlc_event_attach(...)              ((void)0)
#define libvlc_audio_set_volume(...)          ((void)0)
#ifdef __cplusplus
}
#endif
#endif
