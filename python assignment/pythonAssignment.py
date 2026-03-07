#                   PART 1



# used for part 1
import random 
#used for part 2
import numpy as np #type: ignore
import pandas as pd #type: ignore
import matplotlib.pyplot as plt # type: ignore
import seaborn as sns

#generate list of 20 random numbers between 1 and 100
random_list = random.sample(range(1, 100), 20)

#initialize empty even and odd lists for sorting input list into
even = []
odd = []

#for loop for iterating through input list
#if statements to sort even vs. odd; even determinded using modulus operator, 
# if number is dividsible by 2 with no remainder its even
for i in random_list:
    if i % 2 ==0:
        even.append(i)
    else: odd.append(i)

print(random_list)
print("even numbers: ", even)
print("odd numbers: ", odd)


#               PART 2


#set seaborn theme and color palette for plot and grid
sns.set_theme(style="darkgrid", palette="flare")

data = pd.read_csv('C:\\Users\\mnyx0\\OneDrive\\Documents\\ses407\\python-ses407\\python assignment\\O_chem_data.csv') #reads and stores csv into a dataframe using pandas

#converts data frame from wide (multiple columns) to long format (fewer columns) to be used with seaborn
    #id_vars specifies the column to use as identifier (x) variable (temperature)
    #value_vars specifies the columns to unpivot (the compounds)
    #var_name names new column containing names of the unpivoted columns
    #value_name names new column containing values of the unpivoted columns
df_melted = pd.melt(data, 
                    id_vars=['Temperature[C]'], 
                    value_vars=['ethanol_ethylene', 
                                'propanol_propene', 
                                'butanol_butene', 
                                'pentonal_pentene', 
                                'hexanol_hexene', 
                                'heptanol_heptene', 
                                'octanol_octene'], 
                    var_name='compound', 
                    value_name='log_concentration')

plt.figure(figsize = (10, 6)) #plot figure size

#creates scatterplot with seaborn, hue variable sets each compound to a different color
# palette sets color scheme, legend = 'full' forces comprehenseve legend display
sns.scatterplot(data=df_melted,
                x='Temperature[C]', 
                y='log_concentration',
                hue='compound',
                palette="flare_r",
                legend='full',)

# sets the x and y axis labels and the title of the plot
plt.xlabel('temperature (°C)')
plt.ylabel('log-concentration of each compound')
plt.title('Alcohol to Alkene Dehydration Reactions')

plt.show() #display plot