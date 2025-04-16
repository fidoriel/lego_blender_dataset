FROM linuxserver/blender:4.4.0

RUN apt-get update -y; apt-get install wget unzip -y

RUN mkdir /renderer
WORKDIR /renderer

RUN https://library.ldraw.org/library/updates/complete.zip && \
    unzip complete.zip && \
    rm complete.zip


RUN wget https://github.com/TobyLobster/ImportLDraw/releases/download/v1.2.1/importldraw1.2.1.zip && \
    blender -b --python-expr "import bpy; bpy.ops.preferences.addon_install(filepath='./importldraw1.2.1.zip'); bpy.ops.wm.save_userpref()" && \
    rm importldraw1.2.1.zip
