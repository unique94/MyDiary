import asyncio, time, logging, hashlib, json, mistune

from coroweb import get, post

from models import User, Blog

from apis import APIValueError, APIPermissionError, Page

from aiohttp import web

from config import configs



COOKIE_NAME = 'awesession'
_COOKIE_KEY = configs.session.secret


def user2cookie(user, max_age):
    expires = str(int(time.time() + max_age))
    s = '%s-%s-%s-%s' % (user.id, user.passwd, expires, _COOKIE_KEY)
    L = [user.id, expires, hashlib.sha1(s.encode('utf-8')).hexdigest()]
    return '-'.join(L)

def check_admin(request):
    if request.__user__ is None or not request.__user__.admin:
        return False

def api_check_admin(request):
    if request.__user__ is None or not request.__user__.admin:
        raise APIPermissionError()


def text2html(text):
    markdown = mistune.Markdown()
    return markdown(text)


def get_page_index(page_str):
    p = 1
    try:
        p = int(page_str)
    except ValueError as e:
        pass
    if p < 1:
        p = 1
    return p


@get('/')
async def index(request,*, page='1'):
    page_index = get_page_index(page)
    nums = await Blog.findNumber('count(id)')
    p = Page(nums, page_index)
    blogs = await Blog.findAll(orderBy='created_at desc', limit=(p.offset, p.limit))
    return {
        '__template__': 'index.html',
        'blogs': blogs,
        'page': p
    }


@get('/aboutme')
def aboutme():
    return {
        '__template__': 'aboutme.html'
    }



@get('/blog/{id}')
async def get_blog(*, id):
    blog = await Blog.find(id)


    return {
        '__template__': 'blog.html',
        'id': id
    }





@get('/manage')
def manage_index(request,*,  page='1'):
    return {
        '__template__': 'manage_index.html',
        'user': request.__user__,
        'page_index': get_page_index(page)
    }



@get('/manage/blogs/create')
def manage_blogs_create(request):
    if check_admin(request) == False:
        return {
            '__template__': 'manage_index.html',
            'user': request.__user__
        }

    else:
        return {
            '__template__':'create_blog.html'
        }

@get('/manage/blogs/edit')
async def manage_blogs_edit(request, * , id="default"):
    if check_admin(request) == False:
        return {
            '__template__': 'manage_index.html',
            'user': request.__user__
        }
    else:
        return {
            '__template__':'edit_blog.html',
            'id': id
        }




'''
API
'''

@get('/api/blog/{id}')
async def api_get_blog(*, id):
    blog = await Blog.find(id)
    markdo = text2html(blog.__getattr__('content'))
    return dict(html=markdo, blog=blog)






'''
manage api
'''
@post('/api/manage/authenticate')
async def authenticate(*, email, passwd):
    if not email:
        raise APIValueError('email','Invalid email')
    if not passwd:
        raise APIValueError('passwd','Invalid passwd')
    users = await User.findAll('email=?',[email])
    if len(users) == 0:
        raise APIValueError('email','email not exist')
    user = users[0]
    #check passwd
    sha1 = hashlib.sha1()
    sha1.update(user.id.encode('utf-8'))
    sha1.update(b':')
    sha1.update(passwd.encode('utf-8'))
    if user.passwd != sha1.hexdigest():
        raise APIValueError('passwd','Invalid passwd')

    #set cookie
    r = web.Response()
    r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age = 86400, httponly=True)
    user.passwd = '******'
    r.content_type = 'application/json'
    r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
    return r


@get('/api/manage/blogs')
async def api_blogs(request,*, page='1'):
    api_check_admin(request)
    page_index = get_page_index(page)
    nums =  await Blog.findNumber('count(id)')
    p = Page(nums,page_index)
    if nums == 0 :
        return dict(page=p, blogs=())
    blogs = await Blog.findAll(orderBy='created_at desc', limit=(p.offset, p.limit))
    logging.info(p)
    logging.info("==========================>>>>>>>>>>>>>>>>>>>>")
    return dict(page=p, blogs=blogs)



@post('/api/manage/blogs/create')
async def api_create_blog(request, *, name, summary, content):
    api_check_admin(request)
    if not name or not name.strip():
        raise APIValueError('name','name cannot be empty.')
    if not summary or not summary.strip():
        raise APIValueError('summary','summary cannot be empty.')
    if not content or not content.strip():
        raise APIValueError('content','content cannot be empty.')
    blog = Blog(user_id=request.__user__.id, user_name = request.__user__.name, user_image="about://blank", name=name.strip(), summary=summary.strip(), content = content.strip())
    await blog.save()
    return blog


@post('/api/manage/blogs/create/text2html')
def api_create_blog_text2html(request, *, text):
    api_check_admin(request)
    html = text2html(text)
    print((html))
    return html


@post('/api/manage/blogs/{id}/delete')
async def api_delete_blog(request, *, id):
    api_check_admin(request)
    c = await Blog.find(id)
    if c == None:
        raise APIResourceNotFoundError('blog')
    logging.info(c)
    await c.remove()
    return 'remove'


@post('/api/manage/blogs/update')
async def api_update_blog(request,*, id, name, summary, content):
    api_check_admin(request)
    blog = await Blog.find(id)
    if not name or not name.strip():
        raise APIValueError('name','name cannot be empty.')
    if not summary or not summary.strip():
        raise APIValueError('summary','summary cannot be empty.')
    if not content or not content.strip():
        raise APIValueError('content','content cannot be empty.')
    blog.name = name
    blog.summary = summary
    blog.content = content
    await blog.update()
    logging.info(blog)
    return blog
