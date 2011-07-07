set title "Visualization of bugs in 2.13"
set terminal png enhanced
set output "bugs-2.13-visualization.png"

set yrange [0:2.0]

plot 'bugs-dates.txt' with vectors nohead, \
  'release-dates.txt' with vectors nohead ls 2, \
  'extra-dates.txt' with vectors nohead ls 3, \
  'sixmonths-dates.txt' with vectors nohead ls 4


set xrange[550:760]
set output "zoom-2.13-visualization.png"

plot 'bugs-dates.txt' with vectors nohead, \
  'release-dates.txt' with vectors nohead ls 2, \
  'extra-dates.txt' with vectors nohead ls 3, \
  'sixmonths-dates.txt' with vectors nohead ls 4


