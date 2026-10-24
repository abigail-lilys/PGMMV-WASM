// Runtime smoke test v6 (A/B build test: hello_app = FULL_ES2, hello_nofull = no FULL_ES2).
// Background is a DrawNode (not LayerColor, which needs client-side arrays), plus 7 DrawNodes that each differ in ONE factor.
#include "cocos2d.h"
#include <emscripten.h>
#include <stdio.h>
#include <vector>

USING_NS_CC;

struct Probe { const char* name; Vec2 p; };
static std::vector<Probe> g_probes;
static const char* g_stage = "start";
static bool g_readNow = false;

static void chk(const char* tag)
{
    int n = 0;
    GLenum e;
    while ((e = glGetError()) != GL_NO_ERROR && n++ < 8)
        printf("[smoke] GL error 0x%04X after %s\n", e, tag);
}

static void readPixelsReport(const char* tag)
{
    printf("[smoke] px stage=%s %s frames=%u\n", g_stage, tag, (unsigned)Director::getInstance()->getTotalFrames());
    for (const auto& pr : g_probes)
    {
        unsigned char c[4] = {0, 0, 0, 0};
        glReadPixels((int)pr.p.x, (int)pr.p.y, 1, 1, GL_RGBA, GL_UNSIGNED_BYTE, c);
        printf("[smoke]   %-14s (%3d,%3d) = %3u,%3u,%3u\n", pr.name, (int)pr.p.x, (int)pr.p.y, c[0], c[1], c[2]);
    }
}

static void mk(Scene* s, const char* name, Vec2 pos, bool rect, bool circle, float rot, bool action)
{
    auto dn = DrawNode::create();
    if (rect)   dn->drawSolidRect(Vec2(-50, -30), Vec2(50, 30), Color4F(0.9f, 0.4f, 0.2f, 1.0f));     // 230,102,51
    if (circle) dn->drawSolidCircle(Vec2(0, 0), 20, 0, 32, Color4F(0.2f, 0.7f, 0.9f, 1.0f));          // 51,179,230
    dn->setPosition(pos);
    if (rot != 0) dn->setRotation(rot);
    if (action)   dn->runAction(RepeatForever::create(RotateBy::create(4.0f, 360)));
    s->addChild(dn);
    g_probes.push_back({name, pos});
}

static Scene* buildScene()
{
    g_probes.clear();
    auto s = Scene::create();
    auto bg = DrawNode::create();
    bg->drawSolidRect(Vec2(0, 0), Vec2(960, 640), Color4F(0.0f, 0.43f, 0.235f, 1.0f));   // ~0,110,60
    s->addChild(bg);
    mk(s, "rect-static",   Vec2(120, 520), true,  false, 0,  false);
    mk(s, "circle-static", Vec2(280, 520), false, true,  0,  false);
    mk(s, "both-static",   Vec2(440, 520), true,  true,  0,  false);
    mk(s, "rect-rot30",    Vec2(600, 520), true,  false, 30, false);
    mk(s, "rect-action",   Vec2(760, 520), true,  false, 0,  true);
    mk(s, "both-action",   Vec2(200, 300), true,  true,  0,  true);
    mk(s, "both-rot30",    Vec2(480, 300), true,  true,  30, false);
    s->schedule([](float) {
        static int n = 0;
        printf("[smoke] heartbeat %d  frames=%u  t=%.0fms\n", ++n, (unsigned)Director::getInstance()->getTotalFrames(),
               emscripten_get_now());
    }, 2.0f, "smoke_tick");
    return s;
}

class SmokeApp : public Application
{
public:
    virtual void initGLContextAttrs() override
    {
        GLContextAttrs attrs = {8, 8, 8, 8, 24, 8, 0};
        GLView::setGLContextAttrs(attrs);
    }

    virtual bool applicationDidFinishLaunching() override
    {
        auto director = Director::getInstance();
        auto glview = director->getOpenGLView();
        if (!glview)
        {
            glview = GLViewImpl::createWithRect("smoke", Rect(0, 0, 960, 640));
            director->setOpenGLView(glview);
        }
        glview->setDesignResolutionSize(960, 640, ResolutionPolicy::SHOW_ALL);
        director->setDisplayStats(true);
        director->setAnimationInterval(1.0f / 60);
        director->setProjection(Director::Projection::_2D);   // PGMMV is a 2D game

        printf("[smoke] expected: bg ~0,110,60 | rect centre 230,102,51 | circle centre 51,179,230\n");

        director->getEventDispatcher()->addCustomEventListener(Director::EVENT_AFTER_DRAW, [](EventCustom*) {
            static int f = 0;
            ++f;
            if (f <= 2 || g_readNow)
            {
                g_readNow = false;
                char b[24];
                snprintf(b, sizeof b, "frame#%d", f);
                chk(b);
                readPixelsReport(b);
            }
        });

        auto scene = buildScene();
        director->runWithScene(scene);
        scene->scheduleOnce([](float) { g_stage = "2D@3s"; g_readNow = true; }, 3.0f, "st1");
        scene->scheduleOnce([](float) { g_stage = "2D@6s (rotation has moved on)"; g_readNow = true; }, 6.0f, "st2");

        printf("[smoke] applicationDidFinishLaunching done\n");
        return true;
    }

    virtual void applicationDidEnterBackground() override { Director::getInstance()->stopAnimation(); }
    virtual void applicationWillEnterForeground() override { Director::getInstance()->startAnimation(); }
};

int main(int, char**)
{
    static SmokeApp app;
    int r = Application::getInstance()->run();
    printf("[smoke] run() returned %d\n", r);
    return r;
}
