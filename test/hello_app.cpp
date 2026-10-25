// Render regression suite v10: automatic PASS/FAIL for the render paths PGMMV will need.
#include "cocos2d.h"
#include <stdio.h>
#include <stdlib.h>
#include <string>
#include <vector>

USING_NS_CC;

struct Check { std::string name; int x, y, r, g, b, tol; };
static std::vector<Check> g_checks;
static int g_round = 0;

static void addCheck(const char* name, int x, int y, int r, int g, int b, int tol = 4)
{
    g_checks.push_back({name, x, y, r, g, b, tol});
}

static void runChecks(const char* stage)
{
    int pass = 0, fail = 0;
    printf("[test] ---- %s (frames=%u) ----\n", stage, (unsigned)Director::getInstance()->getTotalFrames());
    for (const auto& c : g_checks)
    {
        unsigned char px[4] = {0, 0, 0, 0};
        glReadPixels(c.x, c.y, 1, 1, GL_RGBA, GL_UNSIGNED_BYTE, px);
        bool ok = abs((int)px[0] - c.r) <= c.tol && abs((int)px[1] - c.g) <= c.tol && abs((int)px[2] - c.b) <= c.tol;
        ok ? ++pass : ++fail;
        printf("[test] %s %-34s (%3d,%3d) expect %3d,%3d,%3d got %3u,%3u,%3u\n", ok ? "PASS" : "FAIL", c.name.c_str(),
               c.x, c.y, c.r, c.g, c.b, px[0], px[1], px[2]);
    }
    GLenum e = glGetError();
    printf("[test] SUMMARY %s: pass=%d fail=%d  glError=0x%04X\n", stage, pass, fail, (unsigned)e);
}

static Sprite* spriteFromRGBA(int w, int h, const std::vector<unsigned char>& d)
{
    auto tex = new Texture2D();
    tex->initWithData(d.data(), d.size(), Texture2D::PixelFormat::RGBA8888, w, h, Size(w, h));
    auto s = Sprite::createWithTexture(tex);
    tex->release();
    return s;
}

static Sprite* solidSprite(unsigned char r, unsigned char g, unsigned char b)
{
    std::vector<unsigned char> d(32 * 32 * 4);
    for (int i = 0; i < 32 * 32; ++i) { d[i * 4] = r; d[i * 4 + 1] = g; d[i * 4 + 2] = b; d[i * 4 + 3] = 255; }
    return spriteFromRGBA(32, 32, d);
}

static Sprite* splitSprite()   // left half yellow, right half cyan
{
    std::vector<unsigned char> d(32 * 32 * 4);
    for (int y = 0; y < 32; ++y)
        for (int x = 0; x < 32; ++x)
        {
            unsigned char* p = &d[(y * 32 + x) * 4];
            bool left = x < 16;
            p[0] = left ? 255 : 0; p[1] = 255; p[2] = left ? 0 : 255; p[3] = 255;
        }
    return spriteFromRGBA(32, 32, d);
}

static DrawNode* rectNode(Vec2 pos, float hw, float hh, Color4F c)
{
    auto dn = DrawNode::create();
    dn->drawSolidRect(Vec2(-hw, -hh), Vec2(hw, hh), c);
    dn->setPosition(pos);
    return dn;
}

static LayerColor* squareLayer(Vec2 center, float size, Color4B c)
{
    auto lc = LayerColor::create(c, size, size);
    lc->setPosition(center - Vec2(size / 2, size / 2));
    return lc;
}

static RenderTexture* makeRT(bool depthStencil)
{
    RenderTexture* rt = depthStencil
        ? RenderTexture::create(64, 64, Texture2D::PixelFormat::RGBA8888, GL_DEPTH24_STENCIL8)
        : RenderTexture::create(64, 64, Texture2D::PixelFormat::RGBA8888);
    if (!rt) { printf("[test] RenderTexture::create FAILED (depthStencil=%d)\n", (int)depthStencil); return nullptr; }
    rt->beginWithClear(0, 0, 1, 1);                       // blue
    auto dn = rectNode(Vec2(32, 32), 16, 16, Color4F(1, 1, 0, 1));   // yellow 32x32 in the middle
    dn->visit(Director::getInstance()->getRenderer(), Mat4::IDENTITY, 0);
    rt->end();
    return rt;
}

static Scene* buildScene()
{
    auto s = Scene::create();
    s->addChild(LayerColor::create(Color4B(30, 30, 30, 255)), -100);
    addCheck("bg LayerColor", 940, 620, 30, 30, 30);

    // stencil: green layer clipped to a circle
    auto stencil = DrawNode::create();
    stencil->drawSolidCircle(Vec2(190, 450), 100, 0, 48, Color4F(1, 1, 1, 1));
    auto clip = ClippingNode::create(stencil);
    auto green = LayerColor::create(Color4B(0, 160, 0, 255), 300, 300);
    green->setPosition(Vec2(40, 300));
    clip->addChild(green);
    s->addChild(clip);
    addCheck("clip inside circle", 190, 450, 0, 160, 0);
    addCheck("clip outside circle (corner)", 60, 310, 30, 30, 30);

    auto grad = LayerGradient::create(Color4B(255, 0, 0, 255), Color4B(0, 0, 255, 255));
    grad->setContentSize(Size(200, 200));
    grad->setPosition(Vec2(360, 420));
    s->addChild(grad);
    addCheck("LayerGradient centre", 460, 520, 127, 0, 127, 10);

    s->addChild(rectNode(Vec2(700, 520), 50, 30, Color4F(0.9f, 0.4f, 0.2f, 1)));
    addCheck("DrawNode after gradient", 700, 520, 230, 102, 51);

    auto sp = splitSprite();
    sp->setScale(2.0f); sp->setPosition(Vec2(640, 380));
    s->addChild(sp);
    addCheck("Sprite left half (yellow)", 624, 380, 255, 255, 0);
    addCheck("Sprite right half (cyan)", 656, 380, 0, 255, 255);

    auto sa = solidSprite(255, 255, 0);
    sa->setScale(2.0f); sa->setPosition(Vec2(780, 380)); sa->setOpacity(128);
    s->addChild(sa);
    addCheck("Sprite opacity 128 blend", 780, 380, 143, 143, 15, 8);

    // client-array <-> VAO transitions, repeated
    s->addChild(squareLayer(Vec2(100, 150), 80, Color4B(200, 0, 200, 255)));
    s->addChild(rectNode(Vec2(200, 150), 40, 30, Color4F(0.9f, 0.4f, 0.2f, 1)));
    auto sm = solidSprite(255, 255, 0); sm->setScale(2.0f); sm->setPosition(Vec2(300, 150)); s->addChild(sm);
    s->addChild(squareLayer(Vec2(400, 150), 80, Color4B(200, 0, 200, 255)));
    s->addChild(rectNode(Vec2(500, 150), 40, 30, Color4F(0.2f, 0.7f, 0.9f, 1)));
    addCheck("mix: LayerColor", 100, 150, 200, 0, 200);
    addCheck("mix: DrawNode", 200, 150, 230, 102, 51);
    addCheck("mix: Sprite", 300, 150, 255, 255, 0);
    addCheck("mix: LayerColor again", 400, 150, 200, 0, 200);
    addCheck("mix: DrawNode again", 500, 150, 51, 178, 229);

    if (auto rtA = makeRT(false))
    {
        rtA->setPosition(Vec2(700, 250));
        s->addChild(rtA);
        addCheck("RenderTexture A centre (yellow)", 700, 250, 255, 255, 0);
        addCheck("RenderTexture A edge (blue)", 724, 250, 0, 0, 255);
    }
    if (auto rtB = makeRT(true))
    {
        rtB->setPosition(Vec2(820, 250));
        s->addChild(rtB);
        addCheck("RenderTexture B(depth+stencil) centre", 820, 250, 255, 255, 0);
        addCheck("RenderTexture B(depth+stencil) edge", 844, 250, 0, 0, 255);
    }
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
        director->setProjection(Director::Projection::_2D);

        GLint depthBits = 0, stencilBits = 0;
        glGetIntegerv(GL_DEPTH_BITS, &depthBits);
        glGetIntegerv(GL_STENCIL_BITS, &stencilBits);
        printf("[test] depth bits=%d stencil bits=%d  frame=%.0fx%.0f\n", (int)depthBits, (int)stencilBits,
               glview->getFrameSize().width, glview->getFrameSize().height);

        auto scene = buildScene();
        GLenum e = glGetError();
        printf("[test] scene built, %d checks, glError=0x%04X\n", (int)g_checks.size(), (unsigned)e);

        director->getEventDispatcher()->addCustomEventListener(Director::EVENT_AFTER_DRAW, [](EventCustom*) {
            static int f = 0;
            ++f;
            if (f == 90)  runChecks("round 1 (frame 90)");
            if (f == 300) runChecks("round 2 (frame 300)");
        });
        director->runWithScene(scene);
        printf("[test] applicationDidFinishLaunching done\n");
        return true;
    }
    virtual void applicationDidEnterBackground() override { Director::getInstance()->stopAnimation(); }
    virtual void applicationWillEnterForeground() override { Director::getInstance()->startAnimation(); }
};

int main(int, char**)
{
    static SmokeApp app;
    int r = Application::getInstance()->run();
    printf("[test] run() returned %d\n", r);
    return r;
}
