#!/usr/bin/env python3
"""Amber Volley — neon gravity-volley arcade for ElbowOS."""
from __future__ import annotations

import math
import os
import random
import subprocess
import sys

import pygame

W, H = 1080, 1920
FPS = 30
TITLE = "AMBER VOLLEY"
HANDLE = "x.com/ElbowOS"

VOID = (8, 6, 18)
INK = (22, 10, 28)
WINE = (48, 16, 36)
AMBER = (255, 168, 48)
GOLD = (255, 214, 96)
COPPER = (255, 96, 54)
TEAL = (48, 230, 210)
CREAM = (255, 244, 228)
MAG = (255, 72, 160)
VIOLET = (168, 88, 255)

NET_Y = 980
COURT = pygame.Rect(50, 180, W - 100, 1400)
PW, PH = 196, 28
BR = 22


class Spark:
    __slots__ = ("x", "y", "vx", "vy", "life", "col", "r")

    def __init__(self, x, y, vx, vy, life, col, r=4):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.life, self.col, self.r = life, col, r


class Game:
    def __init__(self, record: bool):
        self.record = record
        self.surf = pygame.Surface((W, H))
        self.clock = pygame.time.Clock()
        self.font_lg = pygame.font.Font(None, 58)
        self.font_md = pygame.font.Font(None, 46)
        self.font_sm = pygame.font.Font(None, 30)
        self.reset()
        self.screen = None
        if not record:
            self.screen = pygame.display.set_mode((W, H))
            pygame.display.set_caption(TITLE)

    def reset(self) -> None:
        self.t = 0.0
        self.you = 0
        self.foe = 0
        self.combo = 0
        self.flash = 0.0
        self.px = W * 0.5
        self.ax = W * 0.5
        self.pv = 0.0
        self.av = 0.0
        self.sparks: list[Spark] = []
        self.pops: list[tuple[str, float, float, float, tuple]] = []
        self.stars = [(random.randint(0, W), random.randint(0, H), random.random()) for _ in range(90)]
        self.running = True
        self.serve(who=1)

    def serve(self, who: int) -> None:
        self.bx = W * 0.5 + random.uniform(-80, 80)
        if who > 0:
            self.by = COURT.bottom - 160
            self.bvx = random.uniform(-220, 220)
            self.bvy = -780
        else:
            self.by = COURT.top + 160
            self.bvx = random.uniform(-220, 220)
            self.bvy = 420
        self.live = True

    def burst(self, x, y, col, n=14) -> None:
        for _ in range(n):
            a = random.uniform(0, math.tau)
            sp = random.uniform(60, 460)
            self.sparks.append(Spark(x, y, math.cos(a) * sp, math.sin(a) * sp,
                                     random.uniform(0.18, 0.5), col, random.randint(3, 7)))

    def paddle_hit(self, x, y, w, incoming: int) -> bool:
        if abs(self.bx - x) > w * 0.5 + BR:
            return False
        if abs(self.by - y) > PH * 0.7 + BR:
            return False
        off = (self.bx - x) / (w * 0.5)
        self.bvx = off * 520 + random.uniform(-40, 40)
        self.bvy = -abs(self.bvy) * 0.18 - 820 if incoming > 0 else abs(self.bvy) * 0.18 + 620
        self.by = y - (PH * 0.5 + BR + 2) if incoming > 0 else y + (PH * 0.5 + BR + 2)
        self.combo += 1
        self.flash = 0.18
        col = COPPER if incoming > 0 else TEAL
        self.burst(self.bx, self.by, col, 12)
        self.pops.append(("SMACK", self.bx, self.by - 30, 0.45, col))
        return True

    def score_point(self, to_you: bool) -> None:
        if to_you:
            self.you += 1
            tag, col = "+YOU", GOLD
        else:
            self.foe += 1
            tag, col = "+RIVAL", TEAL
        self.combo = 0
        self.flash = 0.28
        self.pops.append((tag, W * 0.5, NET_Y - 80, 0.7, col))
        self.burst(self.bx, self.by, col, 22)
        self.serve(who=1 if to_you else -1)

    def steer(self, x, v, target, accel, vmax, dt) -> tuple[float, float]:
        want = max(COURT.left + PW * 0.5, min(COURT.right - PW * 0.5, target))
        if want > x + 8:
            v = min(vmax, v + accel * dt)
        elif want < x - 8:
            v = max(-vmax, v - accel * dt)
        else:
            v *= 0.82
        x = max(COURT.left + PW * 0.5, min(COURT.right - PW * 0.5, x + v * dt))
        return x, v

    def update(self, dt: float) -> None:
        self.t += dt
        self.flash = max(0.0, self.flash - dt)
        predict = self.bx + self.bvx * 0.22
        if self.record:
            if self.bvy > 0 or self.by > NET_Y - 40:
                self.px, self.pv = self.steer(self.px, self.pv, predict + math.sin(self.t * 3) * 18, 2800, 760, dt)
            else:
                self.px, self.pv = self.steer(self.px, self.pv, W * 0.5, 1400, 420, dt)
        if self.bvy < 0 or self.by < NET_Y + 40:
            self.ax, self.av = self.steer(self.ax, self.av, predict + math.sin(self.t * 2.2) * 24, 2400, 700, dt)
        else:
            self.ax, self.av = self.steer(self.ax, self.av, W * 0.5, 1200, 380, dt)
        if self.live:
            self.bvy += 980 * dt
            self.bx += self.bvx * dt
            self.by += self.bvy * dt
            if self.bx < COURT.left + BR:
                self.bx = COURT.left + BR
                self.bvx = abs(self.bvx) * 0.92
                self.burst(self.bx, self.by, AMBER, 6)
            elif self.bx > COURT.right - BR:
                self.bx = COURT.right - BR
                self.bvx = -abs(self.bvx) * 0.92
                self.burst(self.bx, self.by, AMBER, 6)
            if abs(self.by - NET_Y) < 18 + BR and COURT.left + 80 < self.bx < COURT.right - 80:
                self.bvy = -abs(self.bvy) * 0.55 if self.by < NET_Y else abs(self.bvy) * 0.55
                self.by = NET_Y - 22 - BR if self.by < NET_Y else NET_Y + 22 + BR
                self.burst(self.bx, NET_Y, CREAM, 8)
            py = COURT.bottom - 70
            ay = COURT.top + 70
            self.paddle_hit(self.px, py, PW, 1)
            self.paddle_hit(self.ax, ay, PW, -1)
            if self.by > COURT.bottom - BR:
                self.score_point(False)
            elif self.by < COURT.top + BR:
                self.score_point(True)
        live = []
        for sp in self.sparks:
            sp.x += sp.vx * dt
            sp.y += sp.vy * dt + 140 * dt
            sp.life -= dt
            if sp.life > 0:
                live.append(sp)
        self.sparks = live[-220:]
        self.pops = [(a, x, y - 70 * dt, life - dt, c) for a, x, y, life, c in self.pops if life - dt > 0]

    def draw(self, s: pygame.Surface) -> None:
        s.fill(VOID)
        for sx, sy, tw in self.stars:
            yy = int((sy + self.t * (6 + tw * 14)) % H)
            c = 28 + int(tw * 80)
            pygame.draw.circle(s, (c, int(c * 0.55), int(c * 0.35)), (sx, yy), 1 + int(tw * 2))
        pygame.draw.rect(s, INK, COURT, border_radius=28)
        pygame.draw.rect(s, AMBER, COURT, 3, border_radius=28)
        pygame.draw.rect(s, COPPER, COURT, 1, border_radius=28)
        pygame.draw.line(s, WINE, (COURT.left + 30, NET_Y), (COURT.right - 30, NET_Y), 6)
        for i in range(9):
            x = COURT.left + 70 + i * ((COURT.width - 140) / 8)
            pygame.draw.line(s, CREAM, (int(x), NET_Y - 22), (int(x), NET_Y + 22), 3)
        pygame.draw.line(s, GOLD, (COURT.left + 40, NET_Y - 22), (COURT.right - 40, NET_Y - 22), 4)
        pygame.draw.line(s, GOLD, (COURT.left + 40, NET_Y + 22), (COURT.right - 40, NET_Y + 22), 4)
        glow = pygame.Surface((W, 80), pygame.SRCALPHA)
        glow.fill((255, 160, 40, 28))
        s.blit(glow, (0, NET_Y - 40))
        py = COURT.bottom - 70
        ay = COURT.top + 70
        pygame.draw.rect(s, COPPER, pygame.Rect(int(self.px - PW / 2), int(py - PH / 2), PW, PH), border_radius=12)
        pygame.draw.rect(s, CREAM, pygame.Rect(int(self.px - PW / 2), int(py - PH / 2), PW, PH), 2, border_radius=12)
        pygame.draw.rect(s, TEAL, pygame.Rect(int(self.ax - PW / 2), int(ay - PH / 2), PW, PH), border_radius=12)
        pygame.draw.rect(s, CREAM, pygame.Rect(int(self.ax - PW / 2), int(ay - PH / 2), PW, PH), 2, border_radius=12)
        pygame.draw.circle(s, AMBER, (int(self.bx), int(self.by)), BR)
        pygame.draw.circle(s, GOLD, (int(self.bx), int(self.by)), BR, 3)
        pygame.draw.circle(s, CREAM, (int(self.bx - 6), int(self.by - 6)), 6)
        for sp in self.sparks:
            pygame.draw.circle(s, sp.col, (int(sp.x), int(sp.y)), max(1, int(sp.r * sp.life / 0.4)))
        if self.flash > 0:
            veil = pygame.Surface((W, H), pygame.SRCALPHA)
            veil.fill((255, 180, 60, int(70 * self.flash / 0.28)))
            s.blit(veil, (0, 0))
        title = self.font_lg.render(TITLE, True, AMBER)
        s.blit(title, title.get_rect(center=(W // 2, 54)))
        handle = self.font_sm.render(HANDLE, True, VIOLET)
        s.blit(handle, handle.get_rect(center=(W // 2, 106)))
        s.blit(self.font_md.render(f"YOU  {self.you}", True, GOLD), (64, 1610))
        s.blit(self.font_md.render(f"RIVAL  {self.foe}", True, TEAL), (W - 340, 1610))
        s.blit(self.font_sm.render(f"RALLY  x{self.combo}", True, MAG), (W // 2 - 70, 1618))
        hint = self.font_sm.render("gravity volley — smash over the amber net", True, CREAM)
        s.blit(hint, hint.get_rect(center=(W // 2, 1674)))
        for tag, x, y, life, col in self.pops:
            img = self.font_md.render(tag, True, col)
            s.blit(img, img.get_rect(center=(int(x), int(y))))
        foot = self.font_sm.render("A/D or LEFT/RIGHT  R reset  ESC quit", True, (180, 150, 160))
        s.blit(foot, foot.get_rect(center=(W // 2, H - 28)))

    def handle(self, ev) -> None:
        if ev.type == pygame.QUIT:
            self.running = False
        elif ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_ESCAPE:
                self.running = False
            elif ev.key == pygame.K_r:
                self.reset()

    def play(self) -> None:
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            for ev in pygame.event.get():
                self.handle(ev)
            keys = pygame.key.get_pressed()
            target = self.px
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                target -= 400
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                target += 400
            if keys[pygame.K_LEFT] or keys[pygame.K_a] or keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                self.px, self.pv = self.steer(self.px, self.pv, target, 3600, 900, dt)
            self.update(dt)
            self.draw(self.surf)
            self.screen.blit(self.surf, (0, 0))
            pygame.display.flip()

    def record_mp4(self, path: str) -> None:
        cmd = [
            "ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
            "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
            "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-crf", "20", "-preset", "fast", "-movflags", "+faststart", path,
        ]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        frames = FPS * 15
        for i in range(frames):
            self.update(1.0 / FPS)
            self.draw(self.surf)
            proc.stdin.write(pygame.image.tostring(self.surf, "RGB"))
            if i % 30 == 0:
                print(f"frame {i}/{frames}", flush=True)
        proc.stdin.close()
        rc = proc.wait()
        if rc != 0:
            raise SystemExit(f"ffmpeg failed: {rc}")
        print("wrote", path)


def main() -> None:
    record = "--record" in sys.argv or os.environ.get("ELBOWOS_RECORD") == "1"
    play = "--play" in sys.argv
    if record or not play:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    pygame.init()
    pygame.font.init()
    g = Game(record or not play)
    if record or not play:
        out = os.environ.get("ELBOWOS_MP4", "/home/workdir/artifacts/AMBER_VOLLEY_ElbowOS.mp4")
        g.record_mp4(out)
    else:
        g.play()
    pygame.quit()


if __name__ == "__main__":
    main()
