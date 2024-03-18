library(ggplot2)

ggplot(mpg, aes(displ, hwy, colour = class)) + 
  geom_point()