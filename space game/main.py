import pygame
pygame.init()
import random
# ship file loading
space = [pygame.image.load("pic\s1.png"), pygame.image.load(
    "pic\s2.png"), pygame.image.load("pic\s3.png"), pygame.image.load("pic\s4.png"), pygame.image.load("pic\s5.png"), pygame.image.load("pic\s6.png"), pygame.image.load("pic\s7.png"), pygame.image.load("pic\s8.png"), pygame.image.load("pic\s9.png")]
enemy_ship = [pygame.image.load("pic\e1.png"), pygame.image.load(
    "pic\e2.png"), pygame.image.load("pic\e3.png"), pygame.image.load("pic\e4.png"), pygame.image.load("pic\e5.png"), pygame.image.load("pic\e6.png"), pygame.image.load("pic\e7.png"), pygame.image.load("pic\e8.png"), pygame.image.load("pic\e9.png")]
bg=pygame.image.load("pic\\bg.jpg")
score=0
fire_sound=pygame.mixer.Sound("pic\\fire.wav")
hit_sound=pygame.mixer.Sound("pic\hit.wav")
bg_music = pygame.mixer.music.load("pic\\bgg.mp3")
pygame.mixer.music.play(-1)
play=True
# window size
win=pygame.display.set_mode((1280,720))
pygame.display.set_icon(pygame.image.load("pic\icon.png"))
pygame.display.set_caption("Space Advanture")
# 
# 
# classes# 
class space_ship(object):
    def __init__(self,x,y,width,height):
        self.x=x
        self.y=y
        self.width=width
        self.height=height
        self.count=0
        self.stand=False
        self.vel=8
        self.left=False
        self.right=True
        self.up=False
        self.down=False
        self.start=True
        self.spi = pygame.Rect(self.x+10, self.y+5, 45, 68)
    def draw(self,win):
        if self.start:
            if self.count<=27:
                self.count=0
            if self.stand:
                if self.left:
                    win.blit(space[self.count//3],(self.x,self.y))
                    self.count+=1
                if self.right:
                    win.blit(space[self.count//3],(self.x,self.y))
                    self.count += 1
                if self.up:
                    win.blit(space[self.count//3], (self.x, self.y))
                    self.count += 1
                if self.down:
                    win.blit(space[self.count//3], (self.x, self.y))
                    self.count += 1
            else:
                win.blit(space[0],(self.x,self.y))
                self.count=0
            self.spi = pygame.Rect(self.x+10, self.y+5, 45, 68)
    def space_hit(self):
        self.x=60
        self.y=600
        self.count=0
        font1 = pygame.font.SysFont("comicsans", 100)
        text = font1.render("-5", 1, (255, 0, 0))
        win.blit(text, (200, 300))
        pygame.display.update()
        i=0
        while i<=100:
            pygame.time.delay(10)
            i+=1
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
# 
# 
# 
class enemy_space(object):
    def __init__(self,x,y,width,height):
        self.x=x
        self.y=y
        self.width=width
        self.height=height
        self.vel_x=8
        self.vel_y=8
        self.start=True
        self.count=0
        self.move=True
        self.hit=0
        self.hitting=False
        self.health=10
        self.emi = pygame.Rect(self.x, self.y-2, 72, 50)
    def draw(self,win):
        # self.vel_y=random.randint(-400,400)
        if self.start:
            if self.count<=27:
                self.count=0
            if self.vel_x>0:
                if self.x+self.vel_x<=1200:
                    self.x=self.x+self.vel_x
                    win.blit(enemy_ship[self.count//3],(self.x,self.y))
                    self.count+=1
                else:
                    self.vel_x*=-1
                    self.count=0
            if self.vel_x<0:
                if self.x+self.vel_x>10:
                    self.x = self.x+self.vel_x
                    win.blit(enemy_ship[self.count//3],(self.x,self.y))
                    self.count+=1
                else:
                    self.vel_x*=-1
                    self.count=0
            self.emi = pygame.Rect(self.x, self.y-2, 72, 50)
        # life creating
            if score==0:
                pygame.draw.rect(win, (68, 189, 50),(self.x, self.y-10, 40, 10), 0)
            else:
                if score>=10:
                    self.hit=0
                    pygame.draw.rect(win, (68, 189, 50),(self.x, self.y-10, 40, 10), 0)
                while self.hitting:
                    self.hitting=False
                    self.hit+=3
                pygame.draw.rect(win, (68, 189, 50),(self.x, self.y-10, 40, 10), 0)
                pygame.draw.rect(win, (244, 67, 54),(self.x, self.y-10, self.hit, 10), 0)
    def hite(self):
        if self.health>0:
            self.health-=1
        else:
            self.start=False
        self.hitting=True

# 
# 
# 
class projectile(object):
    def __init__(self,x,y,radius,color):
        self.x=x
        self.y=y
        self.radius=radius
        self.color=color
        self.vel=8
        self.pro = pygame.Rect(self.x-5, self.y-7, 10, 12)
    def draw(self,win):
        pygame.draw.circle(win,self.color,(self.x,self.y),self.radius)
        self.pro = pygame.Rect(self.x-5, self.y-7, 10, 12)
# creating objects
ship=space_ship(100,600,10,10)
# 
enemy=enemy_space(200,100,8,8)
# 
gun = projectile(round(ship.x+35), round(ship.y), 6, (255, 255, 255))
# 
# 
clock=pygame.time.Clock()
# 
font = pygame.font.SysFont('gotham bold', 40)
# drawing function
def drawing():
    win.blit(bg,(0,0))
    text = font.render("Score: "+str(score), 1, (245, 246, 250))
    win.blit(text,(10,10))
    ship.draw(win)
    enemy.draw(win)
    for bullet in bullets:
        bullet.draw(win)
    pygame.display.update()
# 
# 
score=0
# for bullets
bullets=[]
bullet_shoot=0
i=0
# 
# main loop
while play:
    clock.tick(27)
    for events in pygame.event.get():
        if events.type==pygame.QUIT:
            play=False
    keys=pygame.key.get_pressed()
    # 
    # multiples enemy:
    # man hit
    if ship.spi.colliderect(enemy.emi):
        score -= 5
        ship.space_hit()
# bullet limit
    if bullet_shoot>0:
        bullet_shoot+=1
    if bullet_shoot>3:
        bullet_shoot=0
    for bullet in bullets:
        try:
            if enemy.start==True:
                if bullet.y-30 <= enemy.y:
                    if bullet.x+bullet.radius > enemy.x and bullet.x-bullet.radius-20 < enemy.x:
                        enemy.hite()
                        bullets.pop(bullets.index(bullet))
                        hit_sound.play()
                        score += 1
                    elif bullet.x+bullet.radius+50 > enemy.x+10 and bullet.x-10 < enemy.x-20:
                        enemy.hite()
                        bullets.pop(bullets.index(bullet))
                        score += 1
            if bullet.y>=5:
                bullet.y-=bullet.vel
            else:
                bullets.pop(bullets.index(bullet)) 
        except:
            pass
    if keys[pygame.K_LEFT] and ship.x>5:
        ship.left=True
        ship.x-=ship.vel
        ship.right=False
        ship.stand=True
    elif keys[pygame.K_RIGHT]and ship.x<1200:
        ship.right=True
        ship.x += ship.vel
        ship.left=False
        ship.stand=True
    if keys[pygame.K_UP]and ship.y>5:
        ship.left=False
        ship.right=False
        ship.stand=True
        ship.down=False
        ship.up=True
        ship.y-=ship.vel
    if keys[pygame.K_DOWN] and ship.y<630:
        ship.left=False
        ship.right=False
        ship.stand=True
        ship.up=False
        ship.down=True
        ship.y+=ship.vel
    if keys[pygame.K_SPACE] and bullet_shoot==0:
        fire_sound.play()
        if len(bullets)<=10:
            gun = projectile(round(ship.x+35), round(ship.y),
                             6, (255, 255, 255))
            bullets.append(gun)
        bullet_shoot=1
    else:
        ship.stand=False
        ship.count=0
    drawing()
    
pygame.quit()
