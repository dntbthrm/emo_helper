import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv("rate_table.csv")

rating_counts = df['rate'].value_counts().sort_index()
use_columns = df['like'].value_counts().sort_index()

colors = {
    1: '#FF9999',
    2: '#FFCC99',
    3: '#FFFF99',
    4: '#99CCFF',
    5: '#99FF99'
}

colors1 = {
    'non_def': '#9AE9F5',
    'no': '#F2634E',
    'yes': '#F27E84'
}
rating_colors = [colors.get(rating, '#CCCCCC') for rating in rating_counts.index]
use_colors = [colors1.get(like, '#CCCCCC') for like in use_columns.index]
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
label_map = {
    "yes": "Да",
    "no": "Нет",
    "non_def": "Не могу сказать"
}
labels = [label_map.get(label, label) for label in use_columns.index]

fig, ax = plt.subplots(figsize=(10, 6))
wedges, texts, autotexts = ax.pie(
    use_columns,
    labels=labels,
    autopct=make_autopct(use_columns),
    colors=use_colors,
    startangle=140,
    textprops=dict(color="black", fontsize=12)
)
ax.axis('equal')
plt.title(f"Опрос: Стало ли удобнее\nопределять эмоции в переписке?", fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig("user_likes_piechart.png", bbox_inches='tight')

