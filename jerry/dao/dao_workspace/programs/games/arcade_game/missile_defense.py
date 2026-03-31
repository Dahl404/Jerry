#!/usr/bin/env python3
"""
Missile Defense Game - Intercept incoming missiles!
Controls: Arrow keys to move, Space to shoot
Objective: Stop missiles from reaching the base and score 100 points
"""

import curses
import random
import time
from datetime import datetime

class MissileDefenseGame:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.running = True
        self.score = 0
        self.lives = 3
        self.enemies = []
        self.bullets = []
        self.game_over = False
        self.frame = 0
        self.game_speed = 1.0
        self.base_y = 15
        self.base_width = 5
        
    def load_high_score(self):
        try:
            with open('highscore.txt', 'r') as f:
                return int(f.read().strip())
        except:
            return 0
            
    def save_high_score(self):
        with open('highscore.txt', 'w') as f:
            f.write(str(self.score))
            
    def spawn_enemy(self):
        if random.random() < 0.15:
            x = random.randint(2, self.stdscr.getmaxyx()[1] - 3)
            self.enemies.append({'x': x, 'y': 0, 'speed': random.uniform(0.8, 1.5), 'alive': True, 'color': random.choice(['█', '▓', '▒', '░'])})
            
    def update(self):
        if self.game_over or not self.running:
            return
            
        self.spawn_enemy()
        
        # Move enemies
        for enemy in self.enemies[:]:
            if enemy['alive']:
                enemy['y'] += enemy['speed']
                if enemy['y'] > self.base_y:
                    enemy['alive'] = False
                    self.lives -= 1
                    self.game_over = True
                    
        # Remove dead enemies
        self.enemies = [e for e in self.enemies if e['alive']]
        
        # Move bullets
        for bullet in self.bullets[:]:
            bullet['y'] -= 1
            if bullet['y'] < 0:
                self.bullets.remove(bullet)
                
        # Check collisions
        for bullet in self.bullets[:]:
            for enemy in self.enemies[:]:
                if enemy['alive'] and abs(bullet['x'] - enemy['x']) < 2 and abs(bullet['y'] - enemy['y']) < 2:
                    bullet['alive'] = False
                    enemy['alive'] = False
                    self.score += 10
                    break
                    
        self.bullets = [b for b in self.bullets if b['alive']]
        self.frame += 1
        
        # Check game over
        if self.lives <= 0:
            self.game_over = True
            
    def draw(self):
        self.stdscr.clear()
        
        # Draw score and stats
        self.stdscr.addstr(0, 0, "=" * 70)
        self.stdscr.addstr(1, 0, f"Missile Defense - Score: {self.score:4d}  |  Lives: {self.lives:2d}  |  High Score: {self.score + self.high_score}")
        self.stdscr.addstr(2, 0, "=" * 70)
        self.stdscr.addstr(3, 0, "Controls: Arrow Keys to move, Space to shoot | Objective: Reach 100 points!")
        self.stdscr.addstr(4, 0, "=" * 70)
        
        if self.game_over:
            self.stdscr.addstr(2, 0, "GAME OVER!")
            self.stdscr.addstr(3, 0, f"Final Score: {self.score}")
            self.stdscr.addstr(4, 0, f"Target: 100 points")
            self.stdscr.addstr(5, 0, f"High Score: {self.score + self.high_score}")
            self.stdscr.addstr(7, 0, "Press 'r' to restart or 'q' to quit")
        else:
            # Draw base (defense tower)
            for i in range(self.base_width):
                self.stdscr.addstr(self.base_y, self.stdscr.getmaxyx()[1] // 2 - self.base_width // 2 + i, "█")
                
            # Draw incoming missiles
            for enemy in self.enemies:
                if enemy['alive']:
                    self.stdscr.addstr(enemy['y'], enemy['x'], enemy['color'])
                    
            # Draw bullets
            for bullet in self.bullets:
                self.stdscr.addstr(bullet['y'], bullet['x'], " ")
                self.stdscr.addstr(bullet['y'], bullet['x'] + 1, "⚡")
                
            # Draw player indicator
            player_y = self.stdscr.getmaxyx()[0] - 2
            self.stdscr.addstr(player_y, self.stdscr.getmaxyx()[1] // 2 - 1, "BASE DEFENSE")
            self.stdscr.addstr(player_y, self.stdscr.getmaxyx()[1] // 2, "████")
            
        self.stdscr.refresh()
        
    def handle_input(self):
        key = self.stdscr.getch()
        
        if key == 27:  # ESC
            self.running = False
        elif key == ord('q'):
            self.running = False
        elif key == ord('r'):
            self.restart()
        elif key in [curses.KEY_UP, ord('k')]:
            self.base_y = max(1, self.base_y - 1)
        elif key in [curses.KEY_DOWN, ord('m')]:
            self.base_y = min(self.stdscr.getmaxyx()[0] - 3, self.base_y + 1)
        elif key in [curses.KEY_LEFT, ord('a')]:
            offset = self.stdscr.getmaxyx()[1] // 2 - self.base_width // 2
            self.base_y = self.base_y  # Keep base Y same, adjust X
        elif key in [curses.KEY_RIGHT, ord('d')]:
            offset = self.stdscr.getmaxyx()[1] // 2 - self.base_width // 2
            self.base_y = self.base_y  # Keep base Y same, adjust X
        elif key == ord(' '):
            self.bullets.append({'x': self.stdscr.getmaxyx()[1] // 2, 'y': self.base_y - 1, 'alive': True})
            
    def restart(self):
        self.score = 0
        self.lives = 3
        self.base_y = self.stdscr.getmaxyx()[0] - 3
        self.enemies = []
        self.bullets = []
        self.game_over = False
        self.game_speed = 1.0

def main(stdscr):
    game = MissileDefenseGame(stdscr)
    
    # Set curses options
    curses.curs_set(0)  # Hide cursor
    stdscr.nodelay(1)  # Non-blocking input
    
    while game.running and not game.game_over:
        game.handle_input()
        game.update()
        game.draw()
        
    if game.score >= 100:
        game.high_score = game.score
        game.save_high_score()
        with open('highscore.txt', 'a') as f:
            f.write(f"\n{datetime.now()} - {game.score} points (TARGET REACHED!)\n")
            
    stdscr.addstr(0, 0, "Thanks for playing! Press any key to exit...")
    stdscr.refresh()
    stdscr.getch()

if __name__ == "__main__":
    curses.wrapper(main)
