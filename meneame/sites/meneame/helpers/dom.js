const loadHiddenComments = async (hiddenComments) => {
  const key = await getCookie('k');
  return Promise.all(
    hiddenComments.map(async (id) => {
      let url = `https://www.meneame.net/backend/get_comment.php?id=${id.replace(
        'cid-',
        ''
      )}&p=0&type=comment&key=${key}`;
      let response = await fetch(url, { method: 'GET' });
      let content = await response.text();
      document.querySelector(`.comment-text[id=${id}]`).innerHTML = content.trim();
    })
  );
};

const getCommentsList = (commentsContainerId) => {
  return new Promise((resolve) => {
    const first = document.querySelector(commentsContainerId);

    const comments = [];
    let link_references = {};

    const list = [first];

    while (list.length > 0) {
      const commentList = list.pop();
      const walker = document.createTreeWalker(commentList, NodeFilter.SHOW_ELEMENT);

      let node = walker.firstChild();

      while (node != null) {
        if (node.classList.contains('threader')) {
          const parent = node.parentNode.parentNode;

          const parentComment = parent.classList.contains('threader')
            ? parent.querySelector('.comment')
            : null;
          const comment = node.querySelector('.comment');

          const internalId = parseInt(
            comment.querySelector('.comment-header > a.comment-order')?.innerText?.replace('#', '')
          );
          const votes = comment
            .querySelector('.comment-footer > span[title="Votos"]')
            ?.innerText?.trim();
          const karma = comment
            .querySelector('.comment-footer > span[title="Karma"]')
            ?.innerText.replace('K ', '')
            ?.trim();
          const author = comment
            .querySelector('.comment-body > .comment-header > .username')
            ?.innerText?.trim();
          const dateTimestamp = comment
            .querySelector('.comment-body > .comment-header > span.comment-date')
            ?.getAttribute('data-ts');

          const isoDate = luxon.DateTime.fromSeconds(parseInt(dateTimestamp), {
            zone: 'Europe/Madrid',
          }).toISO();

          const negative = comment.className.includes('negative');
          const hiddenByModeration = comment.className.includes('phantom');

          const repliesTo = Array.from(
            comment.querySelectorAll('.comment-body > .comment-text > a.tooltip'),
            (e) => {
              const replyId = parseInt(e.innerText.replace('#', ''));
              e.remove();
              return replyId;
            }
          );

          const text = comment.querySelector('.comment-body > .comment-text')?.innerText?.trim();

          const id = (comment.getAttribute('data-id') ?? '').replace('comment-', '');
          const parentId = (parentComment?.getAttribute('data-id') ?? '').replace('comment-', '');

          if (id.length > 0) {
            const item = {
              id,
              internalId,
              isoDate,
              dateTimestamp,
              repliesTo,
              author,
              text,
              votes,
              karma,
              negative,
              hiddenByModeration,
              comments: [],
            };

            if (parentId.length > 0) {
              const link = link_references[parentId];

              if (link instanceof Array) {
                link.push(item);
              }
            } else {
              comments.push(item);
            }

            link_references = {
              ...link_references,
              [id]: item.comments,
            };
          }

          const listNode = node.querySelector('.threader-childs');

          if (listNode) {
            list.push(listNode);
          }
        }
        node = walker.nextSibling();
      }
    }
    resolve(comments);
  });
};

module.exports = {
  loadHiddenComments,
  getCommentsList,
};
