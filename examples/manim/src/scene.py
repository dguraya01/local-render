"""Why render locally? An 8-second Manim explainer.

Render time falls like 1/cores, and a hardware video encoder takes it the rest
of the way down. Uses Text only (no LaTeX needed).
"""
from manim import (
    BLUE_B, DOWN, LEFT, ORIGIN, RIGHT, UP, Arrow, Axes, Create, Dot, FadeIn, FadeOut, GrowArrow, Indicate,
    Scene, Text, ValueTracker, VGroup, Write, always_redraw, config, smooth,
)

INK, LIME, CORAL, PAPER, MUTE = "#0b0d17", "#c6ff3d", "#ff5c39", "#f4f1ea", "#7d84a3"
config.background_color = INK
Text.set_default(font="Helvetica Neue")  # Pango falls back to a system sans if missing


def T(c):
    return 90.0 / c  # minutes of CPU render work spread across c cores


class Main(Scene):
    def construct(self):
        title = Text("Render time vs. CPU cores", font_size=44, color=PAPER, weight="BOLD").to_edge(UP, buff=0.5)
        axes = Axes(
            x_range=[1, 10, 1], y_range=[0, 60, 10], x_length=10, y_length=5.2,
            axis_config={"color": MUTE, "stroke_width": 3, "include_tip": False},
        ).shift(DOWN * 0.45)
        xl = Text("cores", font_size=26, color=MUTE).next_to(axes.x_axis, RIGHT, buff=0.25)
        yl = Text("minutes", font_size=26, color=MUTE).next_to(axes.y_axis, UP, buff=0.15)
        ticks = VGroup(*[Text(str(c), font_size=22, color=MUTE).next_to(axes.c2p(c, 0), DOWN, buff=0.15)
                         for c in (2, 4, 6, 8, 10)],
                       *[Text(str(v), font_size=22, color=MUTE).next_to(axes.c2p(1, v), LEFT, buff=0.15)
                         for v in (20, 40, 60)])
        curve = axes.plot(T, x_range=[1.55, 10], color=BLUE_B, stroke_width=5)

        self.play(Write(title), run_time=0.8)
        self.play(Create(axes), FadeIn(xl, yl, ticks), run_time=1.0)
        self.play(Create(curve), run_time=1.0, rate_func=smooth)

        c = ValueTracker(2)
        dot = always_redraw(lambda: Dot(axes.c2p(c.get_value(), T(c.get_value())), radius=0.13,
                                        color=CORAL if c.get_value() < 5 else LIME))
        label = always_redraw(lambda: Text(
            ("cloud sandbox · 2 cores · ~45 min" if c.get_value() < 2.05
             else "%d cores · ~%d min" % (round(c.get_value()), round(T(round(c.get_value()))))),
            font_size=26, color=CORAL if c.get_value() < 5 else LIME,
        ).next_to(dot, UP + RIGHT, buff=0.15))
        self.play(FadeIn(dot, scale=2), FadeIn(label), run_time=0.4)
        self.wait(0.3)
        self.play(c.animate.set_value(8), run_time=1.4, rate_func=smooth)

        # hardware encoder (VideoToolbox / NVENC) drops it to ~1 minute
        start = axes.c2p(8, T(8))
        end = axes.c2p(8, 1)
        arrow = Arrow(start, end, buff=0.2, color=LIME, stroke_width=6)
        hw = Text("+ hardware encoder", font_size=26, color=LIME).next_to(arrow, LEFT, buff=0.2)
        final = Dot(end, radius=0.16, color=LIME)
        self.play(FadeOut(label), GrowArrow(arrow), FadeIn(hw, shift=LEFT * 0.2), run_time=0.7)
        self.play(FadeIn(final, scale=2.5), run_time=0.3)
        big = Text("~1 min. 45× faster.", font_size=56, color=LIME, weight="BOLD").move_to(ORIGIN + UP * 1.2 + RIGHT * 1.2)
        self.play(Write(big), Indicate(final, color=LIME), run_time=0.8)
        self.wait(1.3)
