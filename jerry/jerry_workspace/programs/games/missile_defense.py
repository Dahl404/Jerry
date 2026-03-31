#!/usr/bin/env python3
"""
MISSILE DEFENSE GAME
====================
Intercept incoming missiles to reach 100 points!
Controls: Arrow keys to move, SPACE to shoot
"""

import curses
import random
import time

class MissileDefense:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.running = True
        self.score = 0
        self.enemies = []
       self.player_x = max(5, self.stdscr.getmaxyx()[1] - 15)
        self.player_y = 25
        self.player_width = min(5, self.stdscr.getmaxyx()[1] - 10)
        
    def update(self):
        if self.game_over or not self.running:
            return
            
        # Spawn enemies
        self.enemy_spawn_timer += 1
        if self.enemy_spawn_timer > 80:  # Every ~1.3 seconds
            self.enemies.append({
                'x': random.randint(5, self.stdscr.getmaxyx()[1] - 5),
                'y': 1,
                'alive': True
            })
            self.enemy_spawn_timer = 0
            
        # Move enemies
        for enemy in self.enemies[:]:
            enemy['y'] += self.enemy_speed
            if enemy['y'] > self.player_y:
                self.enemies.remove(enemy)
                self.game_over = True
                
        # Move bullets
        for bullet in self.bullets[:]:
            bullet['y'] -= 0.5
            if bullet['y'] < 0:
                self.bullets.remove(bullet)
                
        # Check collisions
        for bullet in self.bullets[:]:
            for enemy in self.enemies[:]:
                if enemy['alive']:
                    if abs(bullet['x'] - enemy['x']) < 3 and abs(bullet['y'] - enemy['y']) < 3:
                        bullet['alive'] = False
                        enemy['alive'] = False
                        self.score += 10
                        break
                        
        self.bullets = [b for b in self.bullets if b['alive']]
        
    def draw(self):
        self.stdscr.clear()
        
        # Title
        self.stdscr.addstr(0, 0, "=" * 50)
        self.stdscr.addstr(1, 10, "MISSILE DEFENSE - Score: " + str(self.score))
        self.stdscr.addstr(2, 10, "Target: 100 points | Controls: Arrow keys to move, Space to shoot")
        self.stdscr.addstr(3, 10, "=" * 50)
        
        if self.game_over:
            self.stdscr.addstr(2, 0, "GAME OVER!")
            self.stdscr.addstr(3, 0, "Final Score: " + str(self.score))
            self.stdscr.addstr(4, 0, "Target: 100 points")
            self.stdscr.addstr(5, 0, "Press 'r' to restart or 'q' to quit")
        else:
       else:
            # Draw player
            for i in range(self.player_width):
                self.stdscr.addstr(self.player_y, self.player_x - 2 + i, "█")
            # Draw enemies
            for enemy in self.enemies:
                if enemy['alive']:
                    self.stdscr.addstr(enemy['y'], enemy['x'], "▓")
                    
            # Draw bullets
            for bullet in self.bullets:
                self.stdscr.addstr(bullet['y'], bullet['x'], " ")
                self.stdscr.addstr(bullet['y'], bullet['x'] + 1, "⚡")
        
    def handle_input(self):
        key = self.stdscr.getch()
        
        if key == 27:  # ESC
            self.running = False
        elif key == ord('q'):
            self.running = False
        elif key == ord('r'):
            self.restart()
        elif key in [curses.KEY_UP, ord('k')]:
            self.player_y = max(2, self.player_y - 1)
        elif key in [curses.KEY_DOWN, ord('m')]:
            self.player_y = min(self.stdscr.getmaxyx()[0] - 3, self.player_y + 1)
        elif key in [curses.KEY_LEFT, ord('a')]:
            self.player_x = max(5, self.player_x - 1)
        elif key in [curses.KEY_RIGHT, ord('d')]:
            self.player_x = min(self.stdscr.getmaxyx()[1] - 7, self.player_x + 1)
        elif key == ord(' '):
            self.bullets.append({'x': self.player_x + 1, 'y': self.player_y - 1, 'alive': True})
            
    def restart(self):
        self.score = 0
        self.enemies = []
        self.bullets = []
        self.game_over = False
        self.player_x = 20
        self.player_y = 25

def main(stdscr):
    game = MissileDefense(stdscr)
    
    curses.curs_set(0)
    stdscr.nodelay(1)
    
    while game.running and not game.game_over:
        game.handle_input()
        game.update()
        game.draw()
        
    if game.score >= 100:
        with open('highscore.txt', 'w') as f:
            f.write(str(game.score))
            
    stdscr.addstr(0, 0, "Thanks for playing! Press any key to exit...")
    stdscr.refresh()
    stdscr.getch()

if __name__ == "__main__":
    curses.wrapper(main)
