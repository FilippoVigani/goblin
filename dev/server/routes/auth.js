var express = require('express')
var router = express.Router()
let fs = require('fs')
let crypto = require('crypto');

router.post('/login', function(req, res){
  fs.readfile('../store/users.json', 'utf-8', function(err, users){
    if (err)
      return res.statusCode(500).send({'message': 'Error getting users info'})
    users = JSON.parse(users)
    let user = users.find(user => user.username === req.body.username)
    if (!user)
      return res.statusCode(403).send({'message': 'Wrong user or password'})

    hash = crypto.createHash('sha256')
    if (user.password_hash === hash.update(req.body.password ? req.body.password : '' + user.salt).digest()){
      return res.redirect('/')
    } else {
      return res.statusCode(403).send({'message': 'Wrong user or password'})
    }
  })
})

module.exports = router;
