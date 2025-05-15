import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv("report_table.csv")

rating_counts = df['rate'].value_counts().sort_index()

colors = {
    1: '#FF9999',
    2: '#FFCC99',
    3: '#FFFF99',
    4: '#99CCFF',
    5: '#99FF99'
}
rating_colors = [colors.get(rating, '#CCCCCC') for rating in rating_counts.index]

def make_autopct(values):
    def my_autopct(pct):
        count = int(round(pct * df.shape[0] / 100.0))
        return f'{pct:.1f}%\n({count})'
    return my_autopct

fig, ax = plt.subplots(figsize=(10, 6))
wedges, texts, autotexts = ax.pie(
    rating_counts,
    labels=rating_counts.index,
    autopct=make_autopct(rating_counts),
    colors=rating_colors,
    startangle=140,
    textprops=dict(color="black", fontsize=12)
)
ax.axis('equal')

average_rating = df['rate'].mean()
plt.title(f"Оценки пользователей (средняя: {average_rating:.2f})", fontsize=14, fontweight='bold')

comments = df[df['comment'].str.lower() != 'none'][['username', 'comment']]
if not comments.empty:
    comment_texts = '\n'.join([f"{row['username']}: {row['comment']}" for _, row in comments.iterrows()])
    plt.gcf().text(1.05, 0.5, f"Комментарии:\n\n{comment_texts}", fontsize=10, va='center')

plt.tight_layout()
plt.savefig("user_rating_piechart.png", bbox_inches='tight')

