#!/usr/bin/env python3
"""
Arcade Shooter Game - A high-score tracking shooter game
Controls: Arrow keys to move, Space to shoot
"""

import curses
import random
import os
from datetime import datetime

class Game:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.running = True
        self.score = 0
        self.high_score = self.load_high_score()
        self.player_x = self.stdscr.getmaxyx()[1] // 2
        self.player_y = self.stdscr.getmaxyx()[0] - 2
        self.enemies = []
        self.bullets = []
        self.game_over = False
        self.frame = 0
        
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
        if random.random() < 0.1:
            x = random.randint(2, self.stdscr.getmaxyx()[1] - 3)
            y = 0
            self.enemies.append({'x': x, 'y': y, 'alive': True})
            
    def update(self):
        if self.game_over:
            return
            
        # Spawn enemies
        self.spawn_enemy()
        
        # Move enemies
        for enemy in self.enemies[:]:
            if enemy['alive']:
                enemy['y'] += 1
                if enemy['y'] > self.player_y:
                    enemy['alive'] = False
        
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
        for enemy in self.enemies:
            if enemy['alive'] and enemy['y'] > self.player_y:
                self.game_over = True
                
    def draw(self):
        self.stdscr.clear()
        
        # Draw score
        self.stdscr.addstr(0, 0, f"Score: {self.score}  High Score: {self.high_score}")
        
        if self.game_over:
            self.stdscr.addstr(0, 0, "GAME OVER!")
            self.stdscr.addstr(2, 0, f"Final Score: {self.score}")
            self.stdscr.addstr(4, 0, f"High Score: {self.high_score}")
            self.stdscr.addstr(6, 0, "Press 'r' to restart or 'q' to quit")
        else:
            # Draw player
            self.stdscr.addstr(self.player_y, self.player_x - 1, "██")
            self.stdscr.addstr(self.player_y, self.player_x, " ▄")
            self.stdscr.addstr(self.player_y, self.player_x + 1, " ▄")
            
            # Draw bullets
            for bullet in self.bullets:
                self.stdscr.addstr(bullet['y'], bullet['x'], " ")
                self.stdscr.addstr(bullet['y'], bullet['x'] + 1, "*")
                
            # Draw enemies
            for enemy in self.enemies:
                self.stdscr.addstr(enemy['y'], enemy['x'] - 1, "░░")
                self.stdscr.addstr(enemy['y'], enemy['x'], "░░")
                self.stdscr.addstr(enemy['y'], enemy['x'] + 1, "░░")
                
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
            self.player_y = max(1, self.player_y - 1)
        elif key in [curses.KEY_DOWN, ord('m')]:
            self.player_y = min(self.stdscr.getmaxyx()[0] - 2, self.player_y + 1)
        elif key in [curses.KEY_LEFT, ord('a')]:
            self.player_x = max(1, self.player_x - 1)
        elif key in [curses.KEY_RIGHT, ord('d')]:
            self.player_x = min(self.stdscr.getmaxyx()[1] - 2, self.player_x + 1)
        elif key == ord(' '):
            self.bullets.append({'x': self.player_x + 1, 'y': self.player_y - 1, 'alive': True})
            
    def restart(self):
        self.score = 0
        self.player_x = self.stdscr.getmaxyx()[1] // 2
        self.enemies = []
        self.bullets = []
        self.game_over = False
        
def main(stdscr):
    game = Game(stdscr)
    
    while game.running:
        game.handle_input()
        game.update()
        game.draw()
        
    if game.score > game.high_score:
        game.high_score = game.score
        game.save_high_score()
        with open('highscore.txt', 'a') as f:
            f.write(f"\n{datetime.now()} - {game.score}\n")
            
    stdscr.addstr(0, 0, "Thanks for playing! Press any key to exit...")
    stdscr.refresh()
    stdscr.getch()

if __name__ == "__main__":
    curses.wrapper(main)